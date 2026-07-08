"""
REST API
=========
FastAPI 기반 RESTful API 서버.
모든 신약 개발 모듈을 HTTP 엔드포인트로 제공합니다.
"""

import json
import time
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    modules_available: Dict[str, bool]


class PredictionRequest(BaseModel):
    smiles: str
    model_name: Optional[str] = None


class ADMETResponse(BaseModel):
    smiles: str
    predictions: Dict[str, Any]
    aggregate_score: float
    warnings: List[str] = []


class DockingRequest(BaseModel):
    smiles: str
    receptor_pdbqt: str
    center_x: float
    center_y: float
    center_z: float
    size_x: Optional[float] = 20.0
    size_y: Optional[float] = 20.0
    size_z: Optional[float] = 20.0
    exhaustiveness: Optional[int] = None


class DockingResponse(BaseModel):
    ligand_smiles: str
    best_affinity: float
    num_poses: int
    poses: List[Dict]
    runtime_seconds: float


class GenerationRequest(BaseModel):
    smiles_seeds: List[str]
    num_samples: Optional[int] = 10
    temperature: Optional[float] = 1.0


class GenerationResponse(BaseModel):
    generated_smiles: List[str]
    num_generated: int
    method: str


class PipelineRequest(BaseModel):
    workflow_name: str
    inputs: Optional[Dict[str, Any]] = None


class PipelineStatusResponse(BaseModel):
    pipeline_id: str
    status: str
    progress: float
    stages: List[Dict]


# ──────────────────────────────────────────────────────────
# FastAPI Application Factory
# ──────────────────────────────────────────────────────────


def create_app(config_path: Optional[str] = None) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Configured FastAPI application
    """
    cfg = get_config(config_path)
    api_cfg = cfg.api

    app = FastAPI(
        title="AI Drug Discovery Automation API",
        description="REST API for AI-driven drug discovery pipeline",
        version="2.0.0",
        docs_url=f"{api_cfg.api_prefix}/docs",
        redoc_url=f"{api_cfg.api_prefix}/redoc",
        openapi_url=f"{api_cfg.api_prefix}/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ──────────────────────────────────────────────────────────
    # Health & Info Endpoints
    # ──────────────────────────────────────────────────────────

    @app.get(f"{api_cfg.api_prefix}/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """Check API server health and module availability."""
        modules = {
            "alphafold": _check_module("src.alphafold"),
            "molecular": _check_module("src.molecular"),
            "screening": _check_module("src.screening"),
            "admet": _check_module("src.admet"),
            "generation": _check_module("src.generation"),
            "docking": _check_module("src.docking"),
            "pipeline": _check_module("src.pipeline"),
        }
        return HealthResponse(
            status="healthy",
            version="2.0.0",
            timestamp=datetime.utcnow().isoformat(),
            modules_available=modules,
        )

    @app.get(f"{api_cfg.api_prefix}/config", tags=["System"])
    async def get_config_endpoint():
        """Get current application configuration."""
        return cfg

    # ──────────────────────────────────────────────────────────
    # Molecular Processing Endpoints
    # ──────────────────────────────────────────────────────────

    @app.post(f"{api_cfg.api_prefix}/molecular/descriptors", tags=["Molecular"])
    async def calculate_descriptors(request: PredictionRequest):
        """Calculate molecular descriptors from SMILES."""
        try:
            from src.molecular.rdkit_utils import MolFromSMILES, calculate_all_descriptors
            mol = MolFromSMILES(request.smiles)
            if mol is None:
                raise HTTPException(400, f"Invalid SMILES: {request.smiles}")
            desc = calculate_all_descriptors(mol)
            return {"smiles": request.smiles, "descriptors": desc}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post(f"{api_cfg.api_prefix}/molecular/fingerprints", tags=["Molecular"])
    async def calculate_fingerprints(
        smiles: str = Body(...),
        fingerprint_types: List[str] = Body(["morgan"]),
    ):
        """Calculate molecular fingerprints."""
        try:
            from src.molecular.fingerprint import FingerprintGenerator
            from rdkit import Chem

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise HTTPException(400, f"Invalid SMILES: {smiles}")

            generator = FingerprintGenerator()
            results = {}
            for fp_type in fingerprint_types:
                fp = generator.calculate(mol, fp_type)
                if fp is not None:
                    results[fp_type] = fp.ToBitString() if hasattr(fp, "ToBitString") else str(fp)

            return {"smiles": smiles, "fingerprints": results}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post(f"{api_cfg.api_prefix}/molecular/similarity", tags=["Molecular"])
    async def calculate_similarity(
        smiles1: str = Body(...),
        smiles2: str = Body(...),
        metric: str = Body("tanimoto"),
    ):
        """Calculate similarity between two molecules."""
        try:
            from src.molecular.fingerprint import FingerprintGenerator, similarity
            from rdkit import Chem

            mol1 = Chem.MolFromSmiles(smiles1)
            mol2 = Chem.MolFromSmiles(smiles2)
            if mol1 is None or mol2 is None:
                raise HTTPException(400, "Invalid SMILES")

            fp_gen = FingerprintGenerator()
            fp1 = fp_gen.morgan_fingerprint(mol1)
            fp2 = fp_gen.morgan_fingerprint(mol2)

            sim_value = similarity(fp1, fp2, metric)
            return {
                "smiles1": smiles1,
                "smiles2": smiles2,
                f"{metric}_similarity": sim_value,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    # ──────────────────────────────────────────────────────────
    # ADMET Prediction Endpoints
    # ──────────────────────────────────────────────────────────

    @app.post(f"{api_cfg.api_prefix}/admet/predict", response_model=ADMETResponse, tags=["ADMET"])
    async def predict_admet(request: PredictionRequest):
        """Predict ADMET properties for a molecule."""
        try:
            from src.admet.predictor import ADMETPredictor

            predictor = ADMETPredictor()
            result = predictor.predict(request.smiles)

            return ADMETResponse(
                smiles=request.smiles,
                predictions=result.predictions,
                aggregate_score=result.aggregate_score,
                warnings=result.warnings,
            )
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post(f"{api_cfg.api_prefix}/admet/filter", tags=["ADMET"])
    async def filter_molecule(smiles: str = Body(...), filters: List[str] = Body(["lipinski"])):
        """Apply drug-likeness filters to a molecule."""
        try:
            from src.admet.filters import apply_filters
            from rdkit import Chem

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise HTTPException(400, f"Invalid SMILES: {smiles}")

            results = apply_filters(mol, filters)
            return {"smiles": smiles, "filter_results": results}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    # ──────────────────────────────────────────────────────────
    # Virtual Screening Endpoints
    # ──────────────────────────────────────────────────────────

    @app.post(f"{api_cfg.api_prefix}/screening/similarity", tags=["Screening"])
    async def similarity_search(
        query_smiles: str = Body(...),
        library: List[str] = Body(...),
        top_n: int = Body(10),
        threshold: float = Body(0.5),
    ):
        """Search for similar molecules in a library."""
        try:
            from src.screening.similarity_search import SimilaritySearcher

            searcher = SimilaritySearcher()
            results = searcher.search(query_smiles, library, top_n=top_n, threshold=threshold)
            return {
                "query": query_smiles,
                "results": results,
                "num_results": len(results),
            }
        except Exception as e:
            raise HTTPException(500, str(e))

    # ──────────────────────────────────────────────────────────
    # Molecular Generation Endpoints
    # ──────────────────────────────────────────────────────────

    @app.post(f"{api_cfg.api_prefix}/generation/ga", response_model=GenerationResponse, tags=["Generation"])
    async def generate_with_ga(request: GenerationRequest):
        """Generate molecules using genetic algorithm."""
        try:
            from src.generation.molecular_optimizer import GAOptimizer

            optimizer = GAOptimizer(population_size=request.num_samples)
            result = optimizer.optimize(request.smiles_seeds)

            return GenerationResponse(
                generated_smiles=[result.best_smiles],
                num_generated=1,
                method="genetic_algorithm",
            )
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post(f"{api_cfg.api_prefix}/generation/fragment", tags=["Generation"])
    async def fragment_based_design(
        core_smiles: List[str] = Body(...),
        side_chain_smiles: List[str] = Body(...),
        linker: str = Body("C"),
    ):
        """Generate molecules by fragment linking."""
        try:
            from src.generation.fragment_based import FragmentBasedDesign, MolecularFragment

            designer = FragmentBasedDesign()
            core_frags = [MolecularFragment(smiles=smi, fragment_type="core") for smi in core_smiles]
            sc_frags = [MolecularFragment(smiles=smi, fragment_type="sidechain") for smi in side_chain_smiles]

            if core_frags and sc_frags:
                results = designer.build_from_fragments(core_frags[0], sc_frags, linker)
            else:
                results = []

            return {"generated_smiles": results, "num_generated": len(results), "method": "fragment_based"}
        except Exception as e:
            raise HTTPException(500, str(e))

    # ──────────────────────────────────────────────────────────
    # Docking Endpoints
    # ──────────────────────────────────────────────────────────

    @app.post(f"{api_cfg.api_prefix}/docking/dock", response_model=DockingResponse, tags=["Docking"])
    async def run_docking(request: DockingRequest):
        """Run molecular docking."""
        try:
            from src.docking.autodock_vina import VinaDocker, BindingBox

            docker = VinaDocker()
            if not docker.is_available():
                raise HTTPException(503, "AutoDock Vina is not available")

            binding_box = BindingBox(
                center_x=request.center_x,
                center_y=request.center_y,
                center_z=request.center_z,
                size_x=request.size_x,
                size_y=request.size_y,
                size_z=request.size_z,
            )

            result = docker.dock_smiles(
                smiles=request.smiles,
                receptor_pdbqt=request.receptor_pdbqt,
                binding_box=binding_box,
                exhaustiveness=request.exhaustiveness,
            )

            return DockingResponse(
                ligand_smiles=result.ligand_smiles,
                best_affinity=result.best_affinity,
                num_poses=result.num_poses,
                poses=[p.__dict__ for p in result.poses],
                runtime_seconds=result.runtime_seconds,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    # ──────────────────────────────────────────────────────────
    # Pipeline Endpoints
    # ──────────────────────────────────────────────────────────

    @app.post(f"{api_cfg.api_prefix}/pipeline/run", tags=["Pipeline"])
    async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
        """Run a drug discovery pipeline."""
        try:
            from src.pipeline.workflow_manager import WorkflowManager

            wf_manager = WorkflowManager()

            templates = WorkflowManager.list_templates()
            if request.workflow_name not in templates:
                raise HTTPException(400, f"Unknown workflow: {request.workflow_name}")

            # Get template
            template = getattr(WorkflowManager, request.workflow_name.replace("_", "_"))()
            orchestrator = wf_manager.create_orchestrator(template)

            pipeline_id = f"api_{int(time.time())}"
            background_tasks.add_task(orchestrator.run, request.inputs, pipeline_id)

            return {
                "pipeline_id": pipeline_id,
                "workflow": request.workflow_name,
                "status": "started",
                "message": "Pipeline started in background",
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get(f"{api_cfg.api_prefix}/pipeline/status/{{pipeline_id}}", tags=["Pipeline"])
    async def get_pipeline_status(pipeline_id: str):
        """Get pipeline execution status."""
        from src.pipeline.state_manager import StateManager

        state_manager = StateManager()
        state = state_manager.load_state(pipeline_id)

        if state is None:
            raise HTTPException(404, f"Pipeline not found: {pipeline_id}")

        return PipelineStatusResponse(
            pipeline_id=state.pipeline_id,
            status=state.status,
            progress=len(state.stage_states) / max(1, len(state.stage_states)) * 100,
            stages=[
                {"name": name, "status": status}
                for name, status in state.stage_states.items()
            ],
        )

    @app.get(f"{api_cfg.api_prefix}/pipeline/templates", tags=["Pipeline"])
    async def list_templates():
        """List predefined pipeline workflow templates."""
        templates = WorkflowManager.list_templates()
        return {
            "templates": [{"name": k, "description": v} for k, v in templates.items()],
            "count": len(templates),
        }

    # ──────────────────────────────────────────────────────────
    # AlphaFold Endpoints
    # ──────────────────────────────────────────────────────────

    @app.post(f"{api_cfg.api_prefix}/alphafold/predict", tags=["AlphaFold"])
    async def alphafold_predict(
        sequence: str = Body(...),
        backend: str = Body("colab"),
    ):
        """Predict protein structure using AlphaFold."""
        try:
            from src.alphafold.alphafold_wrapper import AlphaFoldWrapper

            wrapper = AlphaFoldWrapper(backend=backend)
            result = wrapper.predict_structure(sequence)

            return {
                "sequence": sequence[:50] + "...",
                "plddt": result.plddt,
                "status": result.status,
                "pdb_path": result.pdb_path,
                "runtime_seconds": result.runtime_seconds,
            }
        except Exception as e:
            raise HTTPException(500, str(e))

    # ──────────────────────────────────────────────────────────
    # File Upload/Download
    # ──────────────────────────────────────────────────────────

    @app.post(f"{api_cfg.api_prefix}/files/upload", tags=["Files"])
    async def upload_file(file: UploadFile = File(...)):
        """Upload a file (PDB, SDF, SMILES, etc.)."""
        data_dir = Path(cfg.data_dir) / "uploads"
        data_dir.mkdir(parents=True, exist_ok=True)

        filepath = data_dir / file.filename
        content = await file.read()

        with open(filepath, "wb") as f:
            f.write(content)

        return {
            "filename": file.filename,
            "size": len(content),
            "path": str(filepath),
            "content_type": file.content_type,
        }

    @app.get(f"{api_cfg.api_prefix}/files/{{filename}}", tags=["Files"])
    async def download_file(filename: str):
        """Download a file."""
        filepath = Path(cfg.data_dir) / "uploads" / filename
        if not filepath.exists():
            raise HTTPException(404, f"File not found: {filename}")
        return FileResponse(str(filepath))

    return app


def _check_module(module_name: str) -> bool:
    """Check if a module is importable."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


# ──────────────────────────────────────────────────────────
# Global Application Instance
# ──────────────────────────────────────────────────────────

_app: Optional[FastAPI] = None


def get_app(config_path: Optional[str] = None) -> FastAPI:
    """Get or create the global FastAPI application instance."""
    global _app
    if _app is None:
        _app = create_app(config_path)
    return _app
