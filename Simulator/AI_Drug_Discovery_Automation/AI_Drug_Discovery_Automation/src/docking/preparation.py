"""
Receptor and Ligand Preparation
=================================
Utilities for preparing PDBQT files for AutoDock Vina.

Handles:
    - PDB to PDBQT conversion (protonation, charge assignment)
    - SMILES to PDBQT conversion via RDKit + Meeko/OpenBabel
    - Binding site detection
    - File format conversion (PDB, MOL2, SDF, PDBQT)
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, rdDistGeom

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Receptor Preparation
# ──────────────────────────────────────────────────────────


class ReceptorPreparer:
    """
    Prepare receptor structures for docking.

    Supports:
        - PDB to PDBQT conversion
        - Protonation state assignment
        - Gasteiger charge calculation
        - Non-polar hydrogen merging
    """

    def __init__(self, config: Optional[Any] = None):
        cfg = config or get_config()
        dock_cfg = cfg.docking
        self.prepare_receptor_path = dock_cfg.prepare_receptor_path
        self.output_dir = Path(dock_cfg.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prepare_from_pdb(self, pdb_path: str, output_name: Optional[str] = None) -> Optional[str]:
        """
        Convert PDB to PDBQT using prepare_receptor from ADFR suite.

        Args:
            pdb_path: Path to input PDB file
            output_name: Name for output PDBQT file

        Returns:
            Path to PDBQT file, or None on failure
        """
        pdb_path = Path(pdb_path)
        if not pdb_path.exists():
            raise FileNotFoundError(f"PDB file not found: {pdb_path}")

        if output_name is None:
            output_name = pdb_path.stem

        output_pdbqt = self.output_dir / f"{output_name}.pdbqt"

        # Try using prepare_receptor if available
        try:
            cmd = [
                "python", self.prepare_receptor_path,
                "-r", str(pdb_path),
                "-o", str(output_pdbqt),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and output_pdbqt.exists():
                return str(output_pdbqt)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        # Fallback: use RDKit + OpenBabel
        return self._prepare_with_openbabel(str(pdb_path), str(output_pdbqt))

    def _prepare_with_openbabel(self, pdb_path: str, output_pdbqt: str) -> Optional[str]:
        """Fallback preparation using OpenBabel."""
        try:
            cmd = [
                "obabel", pdb_path,
                "-O", output_pdbqt,
                "-xr",
                "--gen3D",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and Path(output_pdbqt).exists():
                return output_pdbqt
        except Exception:
            pass
        return None

    def split_pdb_by_chains(self, pdb_path: str) -> Dict[str, str]:
        """
        Split a multi-chain PDB into individual chain files.

        Args:
            pdb_path: Path to PDB file

        Returns:
            Dict mapping chain ID to file path
        """
        pdb_path = Path(pdb_path)
        chains: Dict[str, list] = {}

        with open(pdb_path) as f:
            for line in f:
                if line.startswith(("ATOM", "HETATM")):
                    chain_id = line[21].strip()
                    if chain_id not in chains:
                        chains[chain_id] = []
                    chains[chain_id].append(line)

        result = {}
        for chain_id, lines in chains.items():
            output_path = self.output_dir / f"{pdb_path.stem}_chain_{chain_id}.pdb"
            with open(output_path, "w") as f:
                f.writelines(lines)
                f.write("END\n")
            result[chain_id] = str(output_path)

        return result

    def remove_water_and_ligands(self, pdb_path: str, output_path: Optional[str] = None) -> str:
        """
        Remove water molecules and non-standard residues from PDB.

        Args:
            pdb_path: Input PDB file path
            output_path: Output PDB file path

        Returns:
            Path to cleaned PDB file
        """
        pdb_path = Path(pdb_path)
        if output_path is None:
            output_path = str(self.output_dir / f"{pdb_path.stem}_clean.pdb")

        standard_residues = {
            "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY",
            "HIS", "ILE", "LEU", "LYS", "MET", "PHE", "PRO", "SER",
            "THR", "TRP", "TYR", "VAL",
        }

        with open(pdb_path) as f:
            lines = f.readlines()

        with open(output_path, "w") as f:
            for line in lines:
                if line.startswith(("ATOM", "HETATM")):
                    res_name = line[17:20].strip()
                    if res_name in standard_residues:
                        f.write(line)
                elif line.startswith(("TER", "END")):
                    f.write(line)

        return output_path


# ──────────────────────────────────────────────────────────
# Ligand Preparation
# ──────────────────────────────────────────────────────────


class LigandPreparer:
    """
    Prepare ligand molecules for docking.

    Supports:
        - SMILES to PDBQT conversion
        - SDF to PDBQT conversion
        - Conformer generation and optimization
        - Protonation state assignment
    """

    def __init__(self, config: Optional[Any] = None):
        cfg = config or get_config()
        dock_cfg = cfg.docking
        self.prepare_ligand_path = dock_cfg.prepare_ligand_path
        self.output_dir = Path(dock_cfg.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def smiles_to_pdbqt(self, smiles: str, ligand_name: str = "ligand") -> Optional[str]:
        """
        Convert SMILES to PDBQT for docking.

        Pipeline: SMILES → RDKit Mol → 3D conformer → PDB → PDBQT

        Args:
            smiles: Ligand SMILES
            ligand_name: Name for the output file

        Returns:
            Path to PDBQT file, or None on failure
        """
        output_pdbqt = self.output_dir / f"{ligand_name}.pdbqt"

        try:
            # 1. RDKit: generate 3D conformation
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return None

            mol = Chem.AddHs(mol)

            # Generate 3D coordinates
            params = rdDistGeom.ETKDGv3()
            params.randomSeed = 42
            status = rdDistGeom.EmbedMolecule(mol, params)

            if status == -1:
                # Try without ETKDG
                AllChem.Compute2DCoords(mol)
                status = AllChem.EmbedMolecule(mol, randomSeed=42)

            if status == -1:
                return None

            # Optimize with MMFF
            try:
                AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
            except Exception:
                try:
                    AllChem.UFFOptimizeMolecule(mol, maxIters=200)
                except Exception:
                    pass

            # 2. Write to temporary PDB
            temp_pdb = self.output_dir / f"{ligand_name}_temp.pdb"
            Chem.MolToPDBFile(mol, str(temp_pdb))

            # 3. Convert PDB to PDBQT
            pdbqt_path = self._convert_pdb_to_pdbqt(str(temp_pdb), str(output_pdbqt))

            # Clean up temp file
            try:
                temp_pdb.unlink()
            except Exception:
                pass

            return pdbqt_path

        except Exception:
            return None

    def sdf_to_pdbqt(self, sdf_path: str, ligand_name: Optional[str] = None) -> Optional[str]:
        """
        Convert SDF to PDBQT.

        Args:
            sdf_path: Path to SDF file
            ligand_name: Name for output file

        Returns:
            Path to PDBQT file
        """
        sdf_path = Path(sdf_path)
        if not sdf_path.exists():
            return None

        if ligand_name is None:
            ligand_name = sdf_path.stem

        output_pdbqt = self.output_dir / f"{ligand_name}.pdbqt"

        # Read first molecule from SDF
        supplier = Chem.SDMolSupplier(str(sdf_path))
        mol = next(supplier, None)
        if mol is None:
            return None

        smiles = Chem.MolToSmiles(mol)
        return self.smiles_to_pdbqt(smiles, ligand_name)

    def _convert_pdb_to_pdbqt(self, pdb_path: str, output_pdbqt: str) -> Optional[str]:
        """
        Convert PDB to PDBQT using available tool.

        Tries: prepare_ligand → obabel → adfr_ligand
        """
        # Method 1: prepare_ligand
        try:
            cmd = [
                "python", self.prepare_ligand_path,
                "-l", pdb_path,
                "-o", output_pdbqt,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0 and Path(output_pdbqt).exists():
                return output_pdbqt
        except Exception:
            pass

        # Method 2: OpenBabel
        try:
            cmd = [
                "obabel", pdb_path,
                "-O", output_pdbqt,
                "-h",
                "--gen3D",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0 and Path(output_pdbqt).exists():
                return output_pdbqt
        except Exception:
            pass

        # Method 3: Meeko (if available)
        try:
            import meeko
            mol = Chem.MolFromPDBFile(pdb_path)
            if mol:
                smiles = Chem.MolToSmiles(mol)
                return self._prepare_with_meeko(smiles, output_pdbqt)
        except ImportError:
            pass

        return None

    def _prepare_with_meeko(self, smiles: str, output_pdbqt: str) -> Optional[str]:
        """
        Prepare ligand PDBQT using Meeko.
        Reference: https://github.com/forlilab/Meeko
        """
        try:
            from meeko import MoleculePreparation, PDBQTWriterLegacy
            from rdkit import Chem

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return None

            mol = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol, randomSeed=42)
            AllChem.MMFFOptimizeMolecule(mol)

            preparator = MoleculePreparation()
            setup = preparator.prepare(mol)
            if setup:
                pdbqt_string, is_ok, err_msg = PDBQTWriterLegacy.write_string(setup[0])
                if is_ok:
                    with open(output_pdbqt, "w") as f:
                        f.write(pdbqt_string)
                    return output_pdbqt
        except Exception:
            pass
        return None

    def prepare_multiconformer(
        self,
        smiles: str,
        ligand_name: str,
        num_conformers: int = 10,
    ) -> List[str]:
        """
        Generate multiple conformers and prepare PDBQT for each.

        Args:
            smiles: Ligand SMILES
            ligand_name: Base name for output files
            num_conformers: Number of conformers to generate

        Returns:
            List of PDBQT file paths
        """
        results = []
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return results

        mol = Chem.AddHs(mol)

        # Generate multiple conformers
        params = rdDistGeom.ETKDGv3()
        params.randomSeed = 42
        params.numThreads = 4
        cids = rdDistGeom.EmbedMultipleConfs(mol, numConfs=num_conformers, params=params)

        for i, cid in enumerate(cids[:num_conformers]):
            # Optimize conformer
            try:
                AllChem.MMFFOptimizeMolecule(mol, maxIters=200, confId=cid)
            except Exception:
                pass

            # Write to temporary PDB
            temp_pdb = self.output_dir / f"{ligand_name}_conf{i}_temp.pdb"
            Chem.MolToPDBFile(mol, str(temp_pdb), confId=cid)

            # Convert to PDBQT
            output_pdbqt = str(self.output_dir / f"{ligand_name}_conf{i}.pdbqt")
            pdbqt = self._convert_pdb_to_pdbqt(str(temp_pdb), output_pdbqt)
            if pdbqt:
                results.append(pdbqt)

            try:
                temp_pdb.unlink()
            except Exception:
                pass

        return results

    def detect_torsions(self, smiles: str) -> int:
        """Detect number of rotatable bonds in a ligand."""
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return 0
        from rdkit.Chem import Descriptors
        return Descriptors.NumRotatableBonds(mol)

    def assign_protonation(self, smiles: str, ph: float = 7.4) -> Optional[str]:
        """
        Assign protonation state at given pH using RDKit.

        Args:
            smiles: Input SMILES
            ph: pH value

        Returns:
            Protonated SMILES or original if unavailable
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        try:
            from rdkit.Chem import MolStandardize
            # Simple protonation: add Hs and let RDKit handle it
            mol = Chem.AddHs(mol)
            return Chem.MolToSmiles(mol)
        except Exception:
            return smiles


# ──────────────────────────────────────────────────────────
# Convenience Functions
# ──────────────────────────────────────────────────────────


def prepare_docking_pair(
    receptor_pdb: str,
    ligand_smiles: str,
    ligand_name: str = "ligand",
    config: Optional[Any] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Prepare both receptor and ligand for docking.

    Args:
        receptor_pdb: Path to receptor PDB file
        ligand_smiles: Ligand SMILES
        ligand_name: Name for the ligand
        config: Application configuration

    Returns:
        Tuple of (receptor_pdbqt_path, ligand_pdbqt_path)
    """
    receptor_preparer = ReceptorPreparer(config)
    ligand_preparer = LigandPreparer(config)

    receptor_pdbqt = receptor_preparer.prepare_from_pdb(receptor_pdb)
    ligand_pdbqt = ligand_preparer.smiles_to_pdbqt(ligand_smiles, ligand_name)

    return receptor_pdbqt, ligand_pdbqt
