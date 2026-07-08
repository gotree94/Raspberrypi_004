"""
Workflow Manager
=================
워크플로우 정의, 템플릿, 실행 계획 관리.
사전 정의된 신약 개발 워크플로우 템플릿을 제공합니다.
"""

import json
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path

from src.pipeline.orchestrator import Stage, PipelineOrchestrator


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    stages: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def add_stage(
        self,
        name: str,
        description: str = "",
        depends_on: Optional[List[str]] = None,
        handler_name: Optional[str] = None,
        handler_kwargs: Optional[Dict] = None,
        timeout_minutes: int = 60,
        retry_attempts: int = 0,
    ) -> "WorkflowDefinition":
        """Add a stage to the workflow definition."""
        stage = {
            "name": name,
            "description": description,
            "depends_on": depends_on or [],
            "handler_name": handler_name,
            "handler_kwargs": handler_kwargs or {},
            "timeout_minutes": timeout_minutes,
            "retry_attempts": retry_attempts,
        }
        self.stages.append(stage)
        return self

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowDefinition":
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowDefinition":
        data = json.loads(json_str)
        return cls.from_dict(data)


class WorkflowManager:
    """
    Workflow definition and management.

    Provides:
        - Predefined drug discovery workflow templates
        - Custom workflow creation
        - Workflow serialization/deserialization
        - Workflow validation
    """

    # ──────────────────────────────────────────────────────────
    # Predefined Workflow Templates
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def full_pipeline() -> WorkflowDefinition:
        """
        Complete drug discovery pipeline workflow.

        Stages:
            1. target_selection → 2. alphafold_prediction
            3. binding_site_detection → 4. library_preparation
            5. virtual_screening → 6. admet_prediction
            7. molecular_generation → 8. molecular_docking
            9. hit_analysis → 10. report_generation
        """
        wf = WorkflowDefinition(
            name="full_pipeline",
            description="Complete end-to-end AI drug discovery pipeline",
            version="2.0.0",
            tags=["full", "end-to-end", "drug-discovery"],
        )

        wf.add_stage(
            name="target_selection",
            description="Select and validate protein target",
        ).add_stage(
            name="alphafold_prediction",
            description="Predict protein 3D structure using AlphaFold",
            depends_on=["target_selection"],
            handler_name="alphafold_prediction",
            timeout_minutes=120,
        ).add_stage(
            name="binding_site_detection",
            description="Detect potential binding sites on target",
            depends_on=["alphafold_prediction"],
        ).add_stage(
            name="library_preparation",
            description="Prepare compound library for screening",
        ).add_stage(
            name="virtual_screening",
            description="Similarity search and pharmacophore screening",
            depends_on=["library_preparation"],
        ).add_stage(
            name="admet_prediction",
            description="Predict ADMET properties for hits",
            depends_on=["virtual_screening"],
        ).add_stage(
            name="molecular_generation",
            description="Generate novel molecules with VAE/GA",
            depends_on=["admet_prediction"],
            timeout_minutes=180,
        ).add_stage(
            name="molecular_docking",
            description="Dock generated molecules to target",
            depends_on=["binding_site_detection", "molecular_generation"],
            timeout_minutes=300,
        ).add_stage(
            name="hit_analysis",
            description="Analyze and rank docking hits",
            depends_on=["molecular_docking"],
        ).add_stage(
            name="report_generation",
            description="Generate final report",
            depends_on=["hit_analysis"],
        )

        return wf

    @staticmethod
    def docking_only() -> WorkflowDefinition:
        """Docking-only workflow for existing structures."""
        wf = WorkflowDefinition(
            name="docking_only",
            description="Virtual screening and docking pipeline",
            version="1.0.0",
            tags=["docking", "screening"],
        )

        wf.add_stage(
            name="receptor_preparation",
            description="Prepare receptor PDBQT",
        ).add_stage(
            name="ligand_preparation",
            description="Prepare ligand library",
        ).add_stage(
            name="batch_docking",
            description="Run batch molecular docking",
            depends_on=["receptor_preparation", "ligand_preparation"],
            timeout_minutes=300,
        ).add_stage(
            name="result_analysis",
            description="Analyze docking results",
            depends_on=["batch_docking"],
        )

        return wf

    @staticmethod
    def generation_only() -> WorkflowDefinition:
        """Molecular generation-only workflow."""
        wf = WorkflowDefinition(
            name="generation_only",
            description="De novo molecular generation pipeline",
            version="1.0.0",
            tags=["generation", "de-novo"],
        )

        wf.add_stage(
            name="seed_preparation",
            description="Prepare seed molecules",
        ).add_stage(
            name="vae_generation",
            description="Generate molecules with VAE",
            depends_on=["seed_preparation"],
            timeout_minutes=120,
        ).add_stage(
            name="ga_optimization",
            description="Optimize with genetic algorithm",
            depends_on=["vae_generation"],
            timeout_minutes=120,
        ).add_stage(
            name="fragment_design",
            description="Fragment-based design",
            depends_on=["ga_optimization"],
        ).add_stage(
            name="admet_filtering",
            description="Filter by ADMET properties",
            depends_on=["fragment_design"],
        )

        return wf

    @staticmethod
    def screening_pipeline() -> WorkflowDefinition:
        """Virtual screening pipeline."""
        wf = WorkflowDefinition(
            name="screening_pipeline",
            description="Virtual screening and hit identification",
            version="1.0.0",
            tags=["screening", "virtual-screening"],
        )

        wf.add_stage(
            name="target_preparation",
            description="Prepare target for screening",
        ).add_stage(
            name="library_screening",
            description="Run similarity and pharmacophore screening",
            depends_on=["target_preparation"],
        ).add_stage(
            name="admet_prediction",
            description="ADMET prediction for hits",
            depends_on=["library_screening"],
        ).add_stage(
            name="hit_selection",
            description="Select final hits for validation",
            depends_on=["admet_prediction"],
        )

        return wf

    # ──────────────────────────────────────────────────────────
    # Workflow Operations
    # ──────────────────────────────────────────────────────────

    def __init__(self, workflow_dir: Optional[str] = None):
        self.workflow_dir = Path(workflow_dir) if workflow_dir else None
        self._handler_registry: Dict[str, Callable] = {}

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a handler function for workflow stages."""
        self._handler_registry[name] = handler

    def create_orchestrator(
        self,
        workflow: WorkflowDefinition,
    ) -> PipelineOrchestrator:
        """
        Create a PipelineOrchestrator from a WorkflowDefinition.

        Args:
            workflow: Workflow definition

        Returns:
            Configured PipelineOrchestrator
        """
        orchestrator = PipelineOrchestrator()

        for stage_def in workflow.stages:
            handler = None
            handler_name = stage_def.get("handler_name")
            if handler_name and handler_name in self._handler_registry:
                handler = self._handler_registry[handler_name]

            stage = Stage(
                name=stage_def["name"],
                description=stage_def.get("description", ""),
                depends_on=stage_def.get("depends_on", []),
                timeout_minutes=stage_def.get("timeout_minutes", 60),
                retry_attempts=stage_def.get("retry_attempts", 0),
                handler=handler,
                handler_kwargs=stage_def.get("handler_kwargs", {}),
            )
            orchestrator.add_stage(stage)

        return orchestrator

    def save_workflow(self, workflow: WorkflowDefinition, name: Optional[str] = None) -> str:
        """Save workflow definition to JSON file."""
        if self.workflow_dir is None:
            raise ValueError("workflow_dir not configured")

        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{name or workflow.name}.json"
        filepath = self.workflow_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(workflow.to_json())

        return str(filepath)

    def load_workflow(self, name_or_path: str) -> WorkflowDefinition:
        """Load workflow definition from JSON file."""
        if self.workflow_dir:
            filepath = self.workflow_dir / f"{name_or_path}.json"
            if filepath.exists():
                with open(filepath, encoding="utf-8") as f:
                    return WorkflowDefinition.from_json(f.read())

        # Try as direct path
        path = Path(name_or_path)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return WorkflowDefinition.from_json(f.read())

        raise FileNotFoundError(f"Workflow not found: {name_or_path}")

    def list_workflows(self) -> List[str]:
        """List available workflow files."""
        if self.workflow_dir is None or not self.workflow_dir.exists():
            return []
        return [f.stem for f in self.workflow_dir.glob("*.json")]

    @staticmethod
    def list_templates() -> Dict[str, str]:
        """List all predefined workflow templates."""
        return {
            "full_pipeline": "Complete end-to-end drug discovery pipeline",
            "docking_only": "Virtual screening and docking only",
            "generation_only": "De novo molecular generation pipeline",
            "screening_pipeline": "Virtual screening and hit identification",
        }
