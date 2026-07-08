"""
AutoDock Vina Wrapper
======================
Python wrapper for AutoDock Vina molecular docking.

Supports:
    - Single and batch docking
    - Flexible residue handling
    - Exhaustiveness and mode control
    - Result parsing and analysis
    - Parallel dockings
"""

import os
import subprocess
import tempfile
import json
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field

import numpy as np

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────


@dataclass
class DockingPose:
    """A single docking pose."""
    mode: int
    affinity: float  # kcal/mol
    rmsd_lower: float
    rmsd_upper: float
    coordinates: Optional[np.ndarray] = None


@dataclass
class DockingResult:
    """Complete docking result for one ligand."""
    ligand_smiles: str
    ligand_name: str
    best_affinity: float
    poses: List[DockingPose] = field(default_factory=list)
    all_affinities: List[float] = field(default_factory=list)
    status: str = "success"
    error_message: str = ""
    runtime_seconds: float = 0.0
    output_pdbqt: Optional[str] = None
    log_file: Optional[str] = None

    @property
    def num_poses(self) -> int:
        return len(self.poses)

    @property
    def mean_affinity(self) -> float:
        if not self.all_affinities:
            return 0.0
        return float(np.mean(self.all_affinities))

    @property
    def affinity_range(self) -> Tuple[float, float]:
        if not self.all_affinities:
            return (0.0, 0.0)
        return (min(self.all_affinities), max(self.all_affinities))

    def to_dict(self) -> Dict:
        return {
            "ligand_smiles": self.ligand_smiles,
            "ligand_name": self.ligand_name,
            "best_affinity": self.best_affinity,
            "num_poses": self.num_poses,
            "mean_affinity": self.mean_affinity,
            "affinity_range": list(self.affinity_range),
            "status": self.status,
            "runtime_seconds": self.runtime_seconds,
            "poses": [
                {
                    "mode": p.mode,
                    "affinity": p.affinity,
                    "rmsd_lower": p.rmsd_lower,
                    "rmsd_upper": p.rmsd_upper,
                }
                for p in self.poses
            ],
        }


@dataclass
class BindingBox:
    """Docking search space (binding site)."""
    center_x: float
    center_y: float
    center_z: float
    size_x: float = 20.0
    size_y: float = 20.0
    size_z: float = 20.0

    def to_vina_args(self) -> List[str]:
        return [
            "--center_x", str(self.center_x),
            "--center_y", str(self.center_y),
            "--center_z", str(self.center_z),
            "--size_x", str(self.size_x),
            "--size_y", str(self.size_y),
            "--size_z", str(self.size_z),
        ]


# ──────────────────────────────────────────────────────────
# Vina Docker
# ──────────────────────────────────────────────────────────


class VinaDocker:
    """
    AutoDock Vina molecular docking interface.

    Handles receptor/ligand preparation, docking execution,
    and result parsing.

    Requirements:
        - AutoDock Vina binary installed and in PATH
        - (Optional) prepare_receptor / prepare_ligand for PDBQT conversion
    """

    def __init__(self, config: Optional[Any] = None):
        cfg = config or get_config()
        dock_cfg = cfg.docking

        self.vina_path = dock_cfg.vina_path
        self.cpu = dock_cfg.cpu
        self.exhaustiveness = dock_cfg.exhaustiveness
        self.num_modes = dock_cfg.num_modes
        self.energy_range = dock_cfg.energy_range
        self.output_dir = Path(dock_cfg.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._check_vina()

    def _check_vina(self) -> bool:
        """Check if AutoDock Vina is available."""
        try:
            result = subprocess.run(
                [self.vina_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def is_available(self) -> bool:
        """Check if Vina is available."""
        return self._check_vina()

    # ──────────────────────────────────────────────────────────
    # Core Docking
    # ──────────────────────────────────────────────────────────

    def dock(
        self,
        receptor_pdbqt: str,
        ligand_pdbqt: str,
        binding_box: BindingBox,
        ligand_name: str = "ligand",
        ligand_smiles: str = "",
        exhaustiveness: Optional[int] = None,
        num_modes: Optional[int] = None,
    ) -> DockingResult:
        """
        Run AutoDock Vina docking.

        Args:
            receptor_pdbqt: Path to receptor PDBQT file
            ligand_pdbqt: Path to ligand PDBQT file
            binding_box: Search space definition
            ligand_name: Name for the ligand
            ligand_smiles: SMILES string (for reference)
            exhaustiveness: Exhaustiveness of search (default: config value)
            num_modes: Maximum number of binding modes (default: config value)

        Returns:
            DockingResult with poses and affinities
        """
        start_time = time.time()
        ex = exhaustiveness or self.exhaustiveness
        nm = num_modes or self.num_modes

        output_pdbqt = str(self.output_dir / f"{ligand_name}_out.pdbqt")
        log_file = str(self.output_dir / f"{ligand_name}_log.txt")

        cmd = [
            self.vina_path,
            "--receptor", receptor_pdbqt,
            "--ligand", ligand_pdbqt,
            "--out", output_pdbqt,
            "--log", log_file,
            "--cpu", str(self.cpu),
            "--exhaustiveness", str(ex),
            "--num_modes", str(nm),
            "--energy_range", str(self.energy_range),
        ]
        cmd.extend(binding_box.to_vina_args())

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )

            if proc.returncode != 0:
                return DockingResult(
                    ligand_smiles=ligand_smiles,
                    ligand_name=ligand_name,
                    best_affinity=0.0,
                    status="error",
                    error_message=proc.stderr.strip(),
                    runtime_seconds=time.time() - start_time,
                    log_file=log_file,
                )

            # Parse results
            poses = self._parse_vina_output(output_pdbqt, log_file)
            best_affinity = min((p.affinity for p in poses), default=0.0)
            all_affinities = [p.affinity for p in poses]

            return DockingResult(
                ligand_smiles=ligand_smiles,
                ligand_name=ligand_name,
                best_affinity=best_affinity,
                poses=poses,
                all_affinities=all_affinities,
                status="success",
                runtime_seconds=time.time() - start_time,
                output_pdbqt=output_pdbqt,
                log_file=log_file,
            )

        except subprocess.TimeoutExpired:
            return DockingResult(
                ligand_smiles=ligand_smiles,
                ligand_name=ligand_name,
                best_affinity=0.0,
                status="error",
                error_message="Docking timed out (600s)",
                runtime_seconds=time.time() - start_time,
            )
        except Exception as e:
            return DockingResult(
                ligand_smiles=ligand_smiles,
                ligand_name=ligand_name,
                best_affinity=0.0,
                status="error",
                error_message=str(e),
                runtime_seconds=time.time() - start_time,
            )

    def dock_smiles(
        self,
        smiles: str,
        receptor_pdbqt: str,
        binding_box: BindingBox,
        ligand_name: Optional[str] = None,
        **kwargs,
    ) -> DockingResult:
        """
        Dock a SMILES string directly (converts to PDBQT first).

        Args:
            smiles: Ligand SMILES
            receptor_pdbqt: Path to receptor PDBQT
            binding_box: Binding site definition
            ligand_name: Optional name for the ligand

        Returns:
            DockingResult
        """
        from src.docking.preparation import LigandPreparer

        preparer = LigandPreparer()
        name = ligand_name or f"lig_{abs(hash(smiles)) % 10000}"

        try:
            ligand_pdbqt = preparer.smiles_to_pdbqt(smiles, name)
            if not ligand_pdbqt:
                return DockingResult(
                    ligand_smiles=smiles,
                    ligand_name=name,
                    best_affinity=0.0,
                    status="error",
                    error_message="Failed to prepare ligand PDBQT",
                )

            return self.dock(
                receptor_pdbqt=receptor_pdbqt,
                ligand_pdbqt=ligand_pdbqt,
                binding_box=binding_box,
                ligand_name=name,
                ligand_smiles=smiles,
                **kwargs,
            )
        except Exception as e:
            return DockingResult(
                ligand_smiles=smiles,
                ligand_name=name,
                best_affinity=0.0,
                status="error",
                error_message=str(e),
            )

    def batch_dock(
        self,
        receptor_pdbqt: str,
        binding_box: BindingBox,
        smiles_list: List[str],
        ligand_names: Optional[List[str]] = None,
        max_concurrent: int = 4,
    ) -> List[DockingResult]:
        """
        Dock multiple ligands sequentially (no native parallel).

        Args:
            receptor_pdbqt: Path to receptor PDBQT
            binding_box: Binding site definition
            smiles_list: List of SMILES strings
            ligand_names: Optional list of ligand names
            max_concurrent: Not used (sequential), kept for API compatibility

        Returns:
            List of DockingResult
        """
        if ligand_names is None:
            ligand_names = [f"lig_{i}" for i in range(len(smiles_list))]

        results = []
        for smi, name in zip(smiles_list, ligand_names):
            result = self.dock_smiles(
                smiles=smi,
                receptor_pdbqt=receptor_pdbqt,
                binding_box=binding_box,
                ligand_name=name,
            )
            results.append(result)

        return results

    # ──────────────────────────────────────────────────────────
    # Score-only mode
    # ──────────────────────────────────────────────────────────

    def score(
        self,
        receptor_pdbqt: str,
        ligand_pdbqt: str,
        binding_box: Optional[BindingBox] = None,
    ) -> float:
        """
        Score-only evaluation (no docking search).

        Args:
            receptor_pdbqt: Path to receptor PDBQT
            ligand_pdbqt: Path to ligand PDBQT
            binding_box: Optional binding box (may be required)

        Returns:
            Binding affinity in kcal/mol (lower = better)
        """
        cmd = [
            self.vina_path,
            "--receptor", receptor_pdbqt,
            "--ligand", ligand_pdbqt,
            "--score_only",
            "--cpu", str(self.cpu),
        ]
        if binding_box:
            cmd.extend(binding_box.to_vina_args())

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                # Parse affinity from output
                match = re.search(r"Affinity:\s*(-?\d+\.?\d*)", proc.stdout)
                if match:
                    return float(match.group(1))
        except Exception:
            pass
        return 0.0

    # ──────────────────────────────────────────────────────────
    # Output Parsing
    # ──────────────────────────────────────────────────────────

    def _parse_vina_output(self, output_pdbqt: str, log_file: str) -> List[DockingPose]:
        """Parse Vina output PDBQT and log file for binding poses."""
        poses = []

        # Try parsing from log file first (more reliable)
        try:
            with open(log_file) as f:
                log_content = f.read()
            poses = self._parse_log_file(log_content)
            if poses:
                return poses
        except (FileNotFoundError, IOError):
            pass

        # Fallback: parse from output PDBQT
        try:
            with open(output_pdbqt) as f:
                pdbqt_content = f.read()
            poses = self._parse_pdbqt_file(pdbqt_content)
        except (FileNotFoundError, IOError):
            pass

        return poses

    def _parse_log_file(self, log_content: str) -> List[DockingPose]:
        """Parse Vina log file for docking results."""
        poses = []
        in_results = False

        for line in log_content.splitlines():
            if "mode | affinity | dist from best" in line:
                in_results = True
                continue
            if in_results:
                # Skip separator lines
                if line.startswith("---") or line.strip() == "":
                    continue
                # Parse data line
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        mode = int(parts[0])
                        affinity = float(parts[1])
                        rmsd_lower = float(parts[2])
                        rmsd_upper = float(parts[3])
                        poses.append(DockingPose(
                            mode=mode,
                            affinity=affinity,
                            rmsd_lower=rmsd_lower,
                            rmsd_upper=rmsd_upper,
                        ))
                    except (ValueError, IndexError):
                        continue

        return poses

    def _parse_pdbqt_file(self, pdbqt_content: str) -> List[DockingPose]:
        """Parse Vina output PDBQT for docking poses."""
        poses = []
        current_mode = 0
        current_affinity = 0.0
        current_rmsd_lower = 0.0
        current_rmsd_upper = 0.0

        for line in pdbqt_content.splitlines():
            if line.startswith("MODEL"):
                current_mode = int(line.split()[1])
            elif "REMARK VINA RESULT:" in line:
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        current_affinity = float(parts[3])
                        current_rmsd_lower = float(parts[4])
                        current_rmsd_upper = float(parts[5])
                    except ValueError:
                        pass
            elif line.startswith("ENDMDL"):
                if current_mode > 0:
                    poses.append(DockingPose(
                        mode=current_mode,
                        affinity=current_affinity,
                        rmsd_lower=current_rmsd_lower,
                        rmsd_upper=current_rmsd_upper,
                    ))
                current_mode = 0
                current_affinity = 0.0

        return poses

    # ──────────────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────────────

    def generate_binding_box_from_pdb(
        self,
        pdb_file: str,
        residue_name: str = "",
        residue_number: int = 0,
        chain: str = "",
        padding: float = 10.0,
    ) -> Optional[BindingBox]:
        """
        Generate a binding box centered on a specific residue.

        Args:
            pdb_file: Path to PDB file
            residue_name: Residue name (e.g., "HEM", "ATP")
            residue_number: Residue number
            chain: Chain identifier
            padding: Padding around the binding site in Angstroms

        Returns:
            BindingBox centered on the residue
        """
        try:
            coords = []
            with open(pdb_file) as f:
                for line in f:
                    if line.startswith("ATOM") or line.startswith("HETATM"):
                        if residue_name:
                            res_name = line[17:20].strip()
                            if res_name != residue_name:
                                continue
                        if residue_number > 0:
                            res_num = int(line[22:26].strip())
                            if res_num != residue_number:
                                continue
                        if chain:
                            chain_id = line[21].strip()
                            if chain_id != chain:
                                continue
                        x = float(line[30:38].strip())
                        y = float(line[38:46].strip())
                        z = float(line[46:54].strip())
                        coords.append((x, y, z))

            if not coords:
                return None

            coords = np.array(coords)
            center = coords.mean(axis=0)
            sizes = coords.max(axis=0) - coords.min(axis=0) + 2 * padding

            return BindingBox(
                center_x=float(center[0]),
                center_y=float(center[1]),
                center_z=float(center[2]),
                size_x=max(float(sizes[0]), 15.0),
                size_y=max(float(sizes[1]), 15.0),
                size_z=max(float(sizes[2]), 15.0),
            )
        except Exception:
            return None

    def sum_results(self, results: List[DockingResult]) -> Dict:
        """Summarize a batch of docking results."""
        if not results:
            return {
                "total": 0,
                "success_rate": 0.0,
                "best_affinity": 0.0,
                "mean_affinity": 0.0,
                "std_affinity": 0.0,
            }

        successful = [r for r in results if r.status == "success"]
        affinities = [r.best_affinity for r in successful]

        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "success_rate": len(successful) / max(1, len(results)) * 100,
            "best_affinity": min(affinities) if affinities else 0.0,
            "mean_affinity": float(np.mean(affinities)) if affinities else 0.0,
            "median_affinity": float(np.median(affinities)) if affinities else 0.0,
            "std_affinity": float(np.std(affinities)) if affinities else 0.0,
            "affinities": affinities,
        }
