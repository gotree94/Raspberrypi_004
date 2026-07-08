"""
AlphaFold Wrapper Module
========================

Low-level wrapper for running AlphaFold2/3 protein structure prediction.
Supports multiple backends: local binary, Docker, and Colab.
"""

import os
import sys
import json
import time
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

import numpy as np

from src.config import AlphaFoldBackend, AlphaFoldConfig, get_config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Custom Exceptions
# ──────────────────────────────────────────────────────────


class AlphaFoldError(Exception):
    """Base exception for AlphaFold-related errors."""
    pass


class AlphaFoldNotInstalledError(AlphaFoldError):
    """Raised when AlphaFold is not installed or not found."""
    pass


class PredictionError(AlphaFoldError):
    """Raised when structure prediction fails."""
    pass


# ──────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────


@dataclass
class AlphafoldResult:
    """
    Contains the results of an AlphaFold structure prediction run.

    Attributes:
        sequence: Input amino acid sequence.
        pdb_path: Path to the predicted PDB file.
        unrelaxed_pdb_path: Path to the unrelaxed PDB file.
        plddt_scores: Per-residue pLDDT confidence scores (0-100).
        mean_plddt: Mean pLDDT score across all residues.
        pae_matrix: Predicted Aligned Error matrix (num_res × num_res).
        max_pae: Maximum PAE value.
        predicted_rmsd: Predicted RMSD from confidence metrics.
        timing: Dictionary of timing information for each pipeline stage.
        metadata: Additional metadata (model used, version, etc.).
        success: Whether the prediction completed successfully.
        error: Error message if prediction failed.
    """
    sequence: str
    pdb_path: Optional[str] = None
    unrelaxed_pdb_path: Optional[str] = None
    plddt_scores: Optional[np.ndarray] = None
    mean_plddt: float = 0.0
    pae_matrix: Optional[np.ndarray] = None
    max_pae: float = 30.0
    predicted_rmsd: Optional[float] = None
    timing: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error: Optional[str] = None

    def __post_init__(self):
        if self.mean_plddt == 0.0 and self.plddt_scores is not None:
            self.mean_plddt = float(np.mean(self.plddt_scores))

    def get_confidence_grade(self) -> str:
        """
        Get the confidence grade based on mean pLDDT.

        Returns:
            'HIGH' (pLDDT > 90), 'CONFIDENT' (pLDDT > 70),
            'LOW' (pLDDT > 50), 'VERY_LOW' (pLDDT <= 50)
        """
        if self.mean_plddt > 90:
            return "HIGH"
        elif self.mean_plddt > 70:
            return "CONFIDENT"
        elif self.mean_plddt > 50:
            return "LOW"
        return "VERY_LOW"

    def get_high_confidence_residues(self, threshold: float = 70.0) -> List[int]:
        """Get indices of residues with pLDDT above threshold."""
        if self.plddt_scores is None:
            return []
        return [int(i) for i, score in enumerate(self.plddt_scores) if score >= threshold]

    def to_dict(self) -> Dict:
        """Convert to dictionary (with numpy arrays converted to lists)."""
        d = asdict(self)
        if self.plddt_scores is not None:
            d["plddt_scores"] = self.plddt_scores.tolist()
            d["mean_plddt"] = float(np.mean(self.plddt_scores))
        if self.pae_matrix is not None:
            d["pae_matrix"] = self.pae_matrix.tolist()
        return d

    def __repr__(self) -> str:
        return (f"AlphafoldResult(mean_pLDDT={self.mean_plddt:.1f}, "
                f"grade={self.get_confidence_grade()}, "
                f"success={self.success})")


# ──────────────────────────────────────────────────────────
# AlphaFold Wrapper
# ──────────────────────────────────────────────────────────


class AlphaFoldWrapper:
    """
    Unified wrapper for AlphaFold2/3 protein structure prediction.

    Supports multiple backends:
        - LOCAL: Run locally installed AlphaFold2 binary
        - DOCKER: Run AlphaFold2 via Docker container
        - COLAB: Run via Google Colab (generates Colab link)
        - LOCAL_ALPHAFOLD3: Run AlphaFold3 (if locally installed)

    Usage:
        wrapper = AlphaFoldWrapper(backend=AlphaFoldBackend.COLAB)
        result = wrapper.predict_structure("MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF")
        print(f"Mean pLDDT: {result.mean_plddt}")
        print(f"PDB saved to: {result.pdb_path}")
    """

    def __init__(
        self,
        backend: AlphaFoldBackend = AlphaFoldBackend.COLAB,
        config: Optional[AlphaFoldConfig] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ):
        """
        Initialize the AlphaFold wrapper.

        Args:
            backend: AlphaFold execution backend.
            config: AlphaFold configuration. Uses global config if None.
            progress_callback: Optional callback for progress updates.
                Signature: callback(stage_name: str, progress: float 0-100)
        """
        self.backend = backend
        self.config = config or get_config().alphafold
        self.progress_callback = progress_callback
        self._validate_backend()

    def _validate_backend(self) -> None:
        """Validate backend availability."""
        if self.backend == AlphaFoldBackend.LOCAL:
            alphafold_dir = self.config.local_alphafold_dir
            if alphafold_dir and not Path(alphafold_dir).exists():
                logger.warning(f"AlphaFold directory not found: {alphafold_dir}")
                if not self._check_command("run_alphafold.py"):
                    logger.warning("AlphaFold does not appear to be installed locally.")
        elif self.backend == AlphaFoldBackend.DOCKER:
            self._check_docker()
        elif self.backend == AlphaFoldBackend.LOCAL_ALPHAFOLD3:
            logger.info("AlphaFold3 backend selected. Ensure AlphaFold3 is properly installed.")

    def _check_command(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            if sys.platform == "win32":
                subprocess.run(["where", cmd], capture_output=True, check=True)
            else:
                subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _check_docker(self) -> None:
        """Check Docker availability."""
        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Docker available: {result.stdout.strip()}")
            else:
                logger.warning("Docker is not available. Install Docker to use the Docker backend.")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("Docker is not available. Install Docker to use the Docker backend.")

    def _report_progress(self, stage: str, progress: float) -> None:
        """Report progress via callback if set."""
        logger.info(f"[{self.backend.value}] {stage}: {progress:.1f}%")
        if self.progress_callback:
            self.progress_callback(stage, progress)

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def predict_structure(
        self,
        sequence: str,
        output_dir: Optional[str] = None,
        job_name: Optional[str] = None,
        num_models: Optional[int] = None,
        use_amber_relax: Optional[bool] = None,
        timeout: Optional[int] = None,
    ) -> AlphafoldResult:
        """
        Predict protein structure from amino acid sequence.

        Args:
            sequence: Amino acid sequence (single-letter codes).
            output_dir: Output directory for results.
            job_name: Job name (default: auto-generated).
            num_models: Number of model ensembles to use (default: config).
            use_amber_relax: Whether to run AMBER relaxation.
            timeout: Timeout in seconds for the prediction.

        Returns:
            AlphafoldResult with prediction results.

        Raises:
            PredictionError: If prediction fails.
            ValueError: If sequence is invalid.
        """
        self._validate_sequence(sequence)

        output_dir = output_dir or self.config.output_dir
        job_name = job_name or f"job_{int(time.time())}"
        num_models = num_models or self.config.num_models
        use_amber_relax = use_amber_relax if use_amber_relax is not None else self.config.use_amber_relax
        timeout = timeout or self.config.timeout_minutes * 60

        self._report_progress("Starting prediction", 0.0)

        # Dispatch to backend-specific implementation
        if self.backend == AlphaFoldBackend.LOCAL:
            result = self._predict_local(sequence, output_dir, job_name, num_models, use_amber_relax, timeout)
        elif self.backend == AlphaFoldBackend.DOCKER:
            result = self._predict_docker(sequence, output_dir, job_name, num_models, use_amber_relax, timeout)
        elif self.backend == AlphaFoldBackend.COLAB:
            result = self._predict_colab(sequence, output_dir, job_name)
        elif self.backend == AlphaFoldBackend.LOCAL_ALPHAFOLD3:
            result = self._predict_alphafold3(sequence, output_dir, job_name, timeout)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

        return result

    def predict_structure_from_fasta(
        self,
        fasta_path: str,
        output_dir: Optional[str] = None,
        **kwargs,
    ) -> AlphafoldResult:
        """
        Predict protein structure from a FASTA file.

        Args:
            fasta_path: Path to FASTA file.
            output_dir: Output directory.
            **kwargs: Additional arguments passed to predict_structure.

        Returns:
            AlphafoldResult with prediction results.
        """
        fasta_path = Path(fasta_path)
        if not fasta_path.exists():
            raise FileNotFoundError(f"FASTA file not found: {fasta_path}")

        # Parse FASTA
        sequence = self._parse_fasta(str(fasta_path))
        if not sequence:
            raise ValueError(f"No sequence found in FASTA file: {fasta_path}")

        job_name = fasta_path.stem
        return self.predict_structure(sequence, output_dir, job_name=job_name, **kwargs)

    def predict_multimer(
        self,
        sequences: List[str],
        output_dir: Optional[str] = None,
        job_name: Optional[str] = None,
        **kwargs,
    ) -> AlphafoldResult:
        """
        Predict multimer protein complex structure.

        Args:
            sequences: List of amino acid sequences (one per chain).
            output_dir: Output directory.
            job_name: Job name.
            **kwargs: Additional arguments.

        Returns:
            AlphafoldResult with multimer prediction results.
        """
        for seq in sequences:
            self._validate_sequence(seq)

        output_dir = output_dir or self.config.output_dir
        job_name = job_name or f"multimer_{int(time.time())}"

        # For multimer, concatenate sequences with separator or use multimer-specific handling
        if self.backend == AlphaFoldBackend.LOCAL_ALPHAFOLD3:
            # AlphaFold3 supports multimer natively
            return self._predict_alphafold3_multimer(sequences, output_dir, job_name, **kwargs)
        else:
            # AlphaFold2: use multimer flag
            concatenated = ":".join(sequences)
            return self._predict_local(
                concatenated, output_dir, job_name,
                is_multimer=True, **kwargs
            )

    def check_status(self) -> Dict[str, Any]:
        """
        Check the status of the AlphaFold installation.

        Returns:
            Dictionary with status information.
        """
        status = {
            "backend": self.backend.value,
            "available": False,
            "version": None,
            "details": {},
        }

        if self.backend == AlphaFoldBackend.LOCAL:
            # Check for AlphaFold files
            af_dir = Path(self.config.local_alphafold_dir)
            if af_dir.exists():
                status["available"] = True
                status["details"]["alphafold_dir"] = str(af_dir)
                # Check for parameter files
                params_dir = af_dir / "params"
                if params_dir.exists():
                    param_files = list(params_dir.glob("*.npz"))
                    status["details"]["param_files"] = len(param_files)
            # Check for run script
            if self._check_command("run_alphafold.py"):
                status["available"] = True

        elif self.backend == AlphaFoldBackend.DOCKER:
            try:
                r = subprocess.run(
                    ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                    capture_output=True, text=True, timeout=10
                )
                images = r.stdout.strip().split("\n")
                af_images = [img for img in images if "alphafold" in img.lower()]
                status["available"] = len(af_images) > 0
                status["details"]["docker_images"] = af_images
            except Exception as e:
                status["details"]["error"] = str(e)

        elif self.backend == AlphaFoldBackend.COLAB:
            status["available"] = True  # Colab is always "available"
            status["details"]["url"] = self.config.colab_url

        return status

    def download_alphafold_params(self, target_dir: Optional[str] = None) -> bool:
        """
        Download AlphaFold model parameters.

        Args:
            target_dir: Target directory for parameters.

        Returns:
            True if download succeeded.
        """
        target_dir = target_dir or str(Path(self.config.data_dir) / "params")
        Path(target_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"To download AlphaFold parameters, please run the setup script:")
        logger.info(f"  cd {self.config.local_alphafold_dir}")
        logger.info(f"  python scripts/download_all_data.py <data_dir>")
        logger.info(f"Data directory: {self.config.data_dir}")

        return False

    # ──────────────────────────────────────────────
    # Backend Implementations
    # ──────────────────────────────────────────────

    def _predict_local(
        self,
        sequence: str,
        output_dir: str,
        job_name: str,
        num_models: int = 5,
        use_amber_relax: bool = True,
        timeout: int = 3600,
        is_multimer: bool = False,
    ) -> AlphafoldResult:
        """Run AlphaFold2 locally."""
        output_path = Path(output_dir) / job_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Write FASTA file
        fasta_path = output_path / f"{job_name}.fasta"
        fasta_path.write_text(f"> {job_name}\n{sequence}\n")

        # Build command
        cmd = [
            sys.executable,
            str(Path(self.config.local_alphafold_dir) / "run_alphafold.py"),
            "--fasta_paths", str(fasta_path),
            "--output_dir", str(output_path),
            "--data_dir", self.config.data_dir,
            "--uniref90_database_path", str(Path(self.config.data_dir) / "uniref90" / "uniref90.fasta"),
            "--mgnify_database_path", str(Path(self.config.data_dir) / "mgnify" / "mgy_proteins.fasta"),
            "--template_date", self.config.max_template_date,
            "--bfd_database_path", str(Path(self.config.data_dir) / "bfd" / "bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt"),
            "--uniclust30_database_path", str(Path(self.config.data_dir) / "uniclust30" / "UniRef30_2021_03"),
            "--pdb70_database_path", str(Path(self.config.data_dir) / "pdb70" / "pdb70"),
            "--num_models", str(num_models),
        ]

        if use_amber_relax:
            cmd.append("--use_amber_relaxation")

        if is_multimer:
            cmd.append("--model_preset=multimer")

        logger.info(f"Running AlphaFold: {' '.join(cmd)}")
        self._report_progress("Running AlphaFold (Local)", 10.0)

        try:
            start_time = time.time()
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=output_path,
            )
            elapsed = time.time() - start_time

            if process.returncode != 0:
                raise PredictionError(
                    f"AlphaFold failed with return code {process.returncode}.\n"
                    f"stdout: {process.stdout[-500:]}\n"
                    f"stderr: {process.stderr[-500:]}"
                )

            self._report_progress("Processing results", 90.0)
            result = self._parse_alphafold_output(output_path, sequence, job_name)
            result.timing["total"] = elapsed
            result.success = True
            logger.info(f"AlphaFold prediction completed in {elapsed:.1f}s. Mean pLDDT: {result.mean_plddt:.1f}")
            self._report_progress("Completed", 100.0)
            return result

        except subprocess.TimeoutExpired:
            raise PredictionError(f"AlphaFold prediction timed out after {timeout}s")
        except FileNotFoundError as e:
            raise AlphaFoldNotInstalledError(
                f"AlphaFold not found at {self.config.local_alphafold_dir}. "
                f"Please check the installation path."
            ) from e

    def _predict_docker(
        self,
        sequence: str,
        output_dir: str,
        job_name: str,
        num_models: int = 5,
        use_amber_relax: bool = True,
        timeout: int = 3600,
    ) -> AlphafoldResult:
        """Run AlphaFold2 via Docker container."""
        output_path = Path(output_dir) / job_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Write FASTA
        fasta_path = output_path / f"{job_name}.fasta"
        fasta_path.write_text(f"> {job_name}\n{sequence}\n")

        # Docker run command
        docker_cmd = [
            "docker", "run",
            "--gpus", "all" if self.config.docker_gpu else "",
            "-v", f"{self.config.data_dir}:/data",
            "-v", f"{output_path}:/output",
            self.config.docker_image,
            "--fasta_paths", f"/output/{job_name}.fasta",
            "--output_dir", "/output",
            "--data_dir", "/data",
            "--max_template_date", self.config.max_template_date,
        ]

        if use_amber_relax:
            docker_cmd.append("--use_amber_relaxation=true")

        # Remove empty strings
        docker_cmd = [c for c in docker_cmd if c]

        logger.info(f"Running AlphaFold Docker: {self.config.docker_image}")
        self._report_progress("Running AlphaFold (Docker)", 10.0)

        try:
            start_time = time.time()
            process = subprocess.run(
                docker_cmd, capture_output=True, text=True, timeout=timeout
            )
            elapsed = time.time() - start_time

            if process.returncode != 0:
                raise PredictionError(
                    f"Docker AlphaFold failed: {process.stderr[-500:]}"
                )

            result = self._parse_alphafold_output(output_path, sequence, job_name)
            result.timing["total"] = elapsed
            result.success = True
            logger.info(f"Docker AlphaFold completed in {elapsed:.1f}s")
            self._report_progress("Completed", 100.0)
            return result

        except subprocess.TimeoutExpired:
            raise PredictionError(f"Docker AlphaFold timed out after {timeout}s")
        except FileNotFoundError:
            raise AlphaFoldNotInstalledError(
                "Docker is not installed or not in PATH."
            )

    def _predict_colab(
        self,
        sequence: str,
        output_dir: str,
        job_name: str,
    ) -> AlphafoldResult:
        """
        Generate a Colab link for AlphaFold prediction.
        Opens Colab notebook with the sequence pre-filled.
        """
        output_path = Path(output_dir) / job_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Save sequence for user reference
        (output_path / f"{job_name}.fasta").write_text(f"> {job_name}\n{sequence}\n")

        # For Colab, we generate a pre-filled URL
        # In practice, users run the Colab and download results back
        colab_url = self.config.colab_url

        logger.info(f"AlphaFold Colab prediction prepared.")
        logger.info(f"Sequence saved to: {output_path / f'{job_name}.fasta'}")
        logger.info(f"To run prediction:")
        logger.info(f"  1. Open: {colab_url}")
        logger.info(f"  2. Paste sequence: {sequence[:50]}...")
        logger.info(f"  3. Run the notebook")
        logger.info(f"  4. Download results to: {output_path}")

        # Return a placeholder result indicating Colab was set up
        result = AlphafoldResult(
            sequence=sequence,
            pdb_path=str(output_path / f"{job_name}.pdb"),
            unrelaxed_pdb_path=str(output_path / f"{job_name}_unrelaxed.pdb"),
            metadata={
                "backend": "colab",
                "colab_url": colab_url,
                "job_name": job_name,
                "status": "ready_for_colab",
            },
            success=False,
            error="Run the Colab notebook to complete prediction. "
                  "See instructions in the log."
        )
        self._report_progress(f"Colab setup complete. Run the notebook.", 100.0)
        return result

    def _predict_alphafold3(
        self,
        sequence: str,
        output_dir: str,
        job_name: str,
        timeout: int = 3600,
    ) -> AlphafoldResult:
        """Run AlphaFold3 prediction (placeholder for actual AlphaFold3 integration)."""
        output_path = Path(output_dir) / job_name
        output_path.mkdir(parents=True, exist_ok=True)

        # AlphaFold3 uses a different input format (JSON)
        af3_input = {
            "name": job_name,
            "sequences": [{"proteinChain": {"sequence": sequence, "count": 1}}],
            "model": {"numDiffusionSteps": 200},
        }

        input_json = output_path / f"{job_name}.json"
        input_json.write_text(json.dumps(af3_input, indent=2))

        logger.info(f"AlphaFold3 input prepared: {input_json}")
        logger.info("AlphaFold3 integration requires the AlphaFold3 server to be running.")
        logger.info("See: https://github.com/google-deepmind/alphafold3")

        result = AlphafoldResult(
            sequence=sequence,
            metadata={
                "backend": "alphafold3",
                "input_json": str(input_json),
                "job_name": job_name,
                "status": "ready_for_af3",
            },
            success=False,
            error="AlphaFold3 server integration needed. "
                  "Input JSON has been prepared."
        )
        return result

    def _predict_alphafold3_multimer(
        self,
        sequences: List[str],
        output_dir: str,
        job_name: str,
        **kwargs,
    ) -> AlphafoldResult:
        """AlphaFold3 multimer prediction."""
        output_path = Path(output_dir) / job_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Build AlphaFold3 input with multiple chains
        chain_data = []
        for i, seq in enumerate(sequences):
            chain_data.append({
                f"proteinChain": {
                    "sequence": seq,
                    "count": 1,
                    "id": f"chain_{i}"
                }
            })

        af3_input = {
            "name": job_name,
            "sequences": chain_data,
            "model": {"numDiffusionSteps": 200},
        }

        input_json = output_path / f"{job_name}.json"
        input_json.write_text(json.dumps(af3_input, indent=2))

        logger.info(f"AlphaFold3 multimer input prepared: {input_json}")

        return AlphafoldResult(
            sequence=":".join(sequences),
            metadata={
                "backend": "alphafold3",
                "input_json": str(input_json),
                "job_name": job_name,
                "num_chains": len(sequences),
                "status": "ready_for_af3_multimer",
            },
            success=False,
        )

    # ──────────────────────────────────────────────
    # Result Parsing
    # ──────────────────────────────────────────────

    def _parse_alphafold_output(
        self,
        output_path: Path,
        sequence: str,
        job_name: str,
    ) -> AlphafoldResult:
        """
        Parse AlphaFold output files and extract confidence metrics.

        Args:
            output_path: Path to the output directory.
            sequence: Input amino acid sequence.
            job_name: Job name.

        Returns:
            AlphafoldResult with parsed data.
        """
        # Find the PDB file
        pdb_files = list(output_path.glob("*.pdb"))
        unrelaxed_pdb = list(output_path.glob("*_unrelaxed.pdb"))
        relaxed_pdb = list(output_path.glob("*_relaxed.pdb"))

        pdb_path = str(relaxed_pdb[0]) if relaxed_pdb else (str(pdb_files[0]) if pdb_files else None)
        unrelaxed_path = str(unrelaxed_pdb[0]) if unrelaxed_pdb else None

        # Parse pLDDT from PDB B-factors
        plddt_scores = None
        if pdb_path:
            plddt_scores = self._parse_plddt_from_pdb(pdb_path)

        # Parse PAE from JSON results
        pae_matrix = None
        result_files = list(output_path.glob("*.json")) + list(output_path.glob("result_*.json"))
        for rf in result_files:
            try:
                data = json.loads(rf.read_text())
                if "pae" in data or "predicted_aligned_error" in data:
                    pae_data = data.get("pae") or data.get("predicted_aligned_error", {})
                    if isinstance(pae_data, dict) and "matrix" in pae_data:
                        pae_matrix = np.array(pae_data["matrix"])
                    elif isinstance(pae_data, list):
                        pae_matrix = np.array(pae_data)
            except (json.JSONDecodeError, KeyError):
                continue

        # Compute metrics
        mean_plddt = float(np.mean(plddt_scores)) if plddt_scores is not None else 0.0
        max_pae = float(np.max(pae_matrix)) if pae_matrix is not None else 30.0

        return AlphafoldResult(
            sequence=sequence,
            pdb_path=pdb_path,
            unrelaxed_pdb_path=unrelaxed_path,
            plddt_scores=plddt_scores,
            mean_plddt=mean_plddt,
            pae_matrix=pae_matrix,
            max_pae=max_pae,
            metadata={"job_name": job_name, "output_dir": str(output_path)},
        )

    @staticmethod
    def _parse_plddt_from_pdb(pdb_path: str) -> np.ndarray:
        """
        Extract per-residue pLDDT scores from PDB file B-factor column.

        In AlphaFold PDB output, the B-factor column (columns 61-66)
        contains the per-residue pLDDT confidence score.

        Args:
            pdb_path: Path to PDB file.

        Returns:
            Numpy array of pLDDT scores.
        """
        plddt_by_residue = {}
        with open(pdb_path) as f:
            for line in f:
                if line.startswith(("ATOM", "HETATM")):
                    try:
                        residue_id = line[22:26].strip() + "_" + line[21:22].strip()
                        b_factor = float(line[60:66].strip())
                        if residue_id not in plddt_by_residue:
                            plddt_by_residue[residue_id] = []
                        plddt_by_residue[residue_id].append(b_factor)
                    except (ValueError, IndexError):
                        continue

        # Average B-factor per residue
        scores = []
        for res_id in sorted(plddt_by_residue.keys()):
            scores.append(np.mean(plddt_by_residue[res_id]))

        return np.array(scores) if scores else np.array([])

    @staticmethod
    def _parse_fasta(fasta_path: str) -> str:
        """Parse a FASTA file and return the protein sequence."""
        sequences = []
        with open(fasta_path) as f:
            current_seq = []
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if current_seq:
                        sequences.append("".join(current_seq))
                        current_seq = []
                elif line:
                    current_seq.append(line)
            if current_seq:
                sequences.append("".join(current_seq))

        return sequences[0] if sequences else ""

    @staticmethod
    def _validate_sequence(sequence: str) -> None:
        """
        Validate an amino acid sequence.

        Args:
            sequence: Amino acid sequence.

        Raises:
            ValueError: If sequence is empty or contains invalid characters.
        """
        if not sequence:
            raise ValueError("Sequence is empty.")

        if len(sequence) < 5:
            raise ValueError(f"Sequence too short ({len(sequence)} residues). Minimum 5 residues.")

        if len(sequence) > 5000:
            raise ValueError(f"Sequence too long ({len(sequence)} residues). Maximum 5000 residues.")

        valid_aas = set("ACDEFGHIKLMNPQRSTVWY")
        upper_seq = sequence.upper()
        invalid = set(upper_seq) - valid_aas
        if invalid:
            raise ValueError(f"Invalid amino acid characters: {invalid}")
