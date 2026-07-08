"""
PDB Processor Module
====================

PDB file processing utilities for protein structure analysis,
format conversion, and quality assessment.
"""

import os
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass

import numpy as np

from src.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class StructureMetrics:
    """Protein structure quality metrics."""
    num_residues: int = 0
    num_chains: int = 0
    num_atoms: int = 0
    num_water: int = 0
    num_ligands: int = 0
    resolution: Optional[float] = None
    mean_plddt: Optional[float] = None
    ramachandran_favored: Optional[float] = None
    clash_score: Optional[float] = None
    completeness: float = 0.0


class PDBProcessor:
    """
    PDB file processor for structure analysis and format conversion.

    Provides utilities for:
    - Extracting chains, residues, and sequences from PDB files
    - Computing RMSD between structures
    - Extracting confidence scores (pLDDT from B-factors)
    - Converting PDB to PDBQT format (for AutoDock)
    - Structure validation and quality assessment
    - Basic visualization setup

    Usage:
        processor = PDBProcessor()
        seq = processor.extract_residue_sequence("protein.pdb")
        scores = processor.extract_confidence_scores("protein.pdb")
        rmsd = processor.compute_rmsd("ref.pdb", "mobile.pdb")
    """

    @staticmethod
    def extract_chain(pdb_path: str, chain_id: str = "A") -> str:
        """
        Extract a specific chain from a PDB file.

        Args:
            pdb_path: Path to PDB file.
            chain_id: Chain identifier (default: 'A').

        Returns:
            PDB content string for the specified chain.
        """
        chain_lines = []
        with open(pdb_path) as f:
            for line in f:
                if line.startswith(("ATOM", "HETATM", "TER")):
                    if len(line) > 21 and line[21].strip() == chain_id:
                        chain_lines.append(line)
                elif line.startswith("END"):
                    chain_lines.append(line)

        return "".join(chain_lines)

    @staticmethod
    def extract_residue_sequence(pdb_path: str, chain_id: Optional[str] = None) -> str:
        """
        Extract the amino acid sequence from a PDB file.

        Uses the three-letter to one-letter code mapping
        from the residue name column (columns 17-20).

        Args:
            pdb_path: Path to PDB file.
            chain_id: Optional chain ID filter.

        Returns:
            One-letter amino acid sequence string.
        """
        aa_3to1 = {
            "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D",
            "CYS": "C", "GLN": "Q", "GLU": "E", "GLY": "G",
            "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
            "MET": "M", "PHE": "F", "PRO": "P", "SER": "S",
            "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
            "HID": "H", "HIE": "H", "HIP": "H",
            "CYX": "C", "CYM": "C",
            "ASH": "D", "GLH": "E",
            "LYN": "K",
            "MSE": "M",  # Selenomethionine
        }

        seen_residues = set()
        sequence_parts = []

        with open(pdb_path) as f:
            for line in f:
                if line.startswith("ATOM") and len(line) >= 23:
                    res_name = line[17:20].strip()
                    chain = line[21].strip() if len(line) > 21 else ""
                    res_seq = line[22:26].strip()

                    # Apply chain filter
                    if chain_id and chain != chain_id:
                        continue

                    # Unique residue identifier
                    res_key = (chain, res_seq, res_name)

                    if res_key not in seen_residues:
                        seen_residues.add(res_key)
                        aa = aa_3to1.get(res_name, "X")
                        sequence_parts.append((chain, int(res_seq) if res_seq.isdigit() else 0, aa))

        # Sort by chain and residue number
        sequence_parts.sort(key=lambda x: (x[0], x[1]))

        return "".join(aa for _, _, aa in sequence_parts)

    @staticmethod
    def compute_rmsd(
        pdb_ref: str,
        pdb_mobile: str,
        selection: str = "CA",
        superimpose: bool = True,
    ) -> float:
        """
        Compute RMSD between two PDB structures.

        Uses Kabsch algorithm for optimal superposition.
        Falls back to simple coordinate comparison if Biopython is unavailable.

        Args:
            pdb_ref: Reference PDB file path.
            pdb_mobile: Mobile PDB file path to align.
            selection: Atom selection ('CA', 'backbone', 'all').
            superimpose: Whether to superimpose structures before RMSD.

        Returns:
            RMSD value in Ångströms.
        """
        try:
            # Try using Biopython for accurate superposition
            from Bio.PDB import PDBParser, Superimposer, Selection as BioSelect
            from Bio.PDB.vectors import Vector

            parser = PDBParser(QUIET=True)
            ref_struct = parser.get_structure("ref", pdb_ref)
            mob_struct = parser.get_structure("mob", pdb_mobile)

            # Select atoms
            ref_atoms = BioSelect.unfold_entities(ref_struct, "A") if selection == "all" else []
            mob_atoms = BioSelect.unfold_entities(mob_struct, "A") if selection == "all" else []

            if selection == "CA":
                ref_atoms = [a for a in ref_struct.get_atoms() if a.get_id() == "CA"]
                mob_atoms = [a for a in mob_struct.get_atoms() if a.get_id() == "CA"]

            if len(ref_atoms) != len(mob_atoms):
                logger.warning(f"Atom count mismatch: {len(ref_atoms)} vs {len(mob_atoms)}")
                # Use the minimum count
                n = min(len(ref_atoms), len(mob_atoms))
                ref_atoms = ref_atoms[:n]
                mob_atoms = mob_atoms[:n]

            if len(ref_atoms) < 3:
                logger.warning("Too few atoms for RMSD calculation")
                return 0.0

            if superimpose:
                super_imposer = Superimposer()
                super_imposer.set_atoms(ref_atoms, mob_atoms)
                super_imposer.apply(mob_atoms)
                rmsd = super_imposer.rms
            else:
                # Simple RMSD without superposition
                rmsd = np.sqrt(np.mean([
                    np.sum((a1.get_vector().get_array() - a2.get_vector().get_array()) ** 2)
                    for a1, a2 in zip(ref_atoms, mob_atoms)
                ]))

            return float(rmsd)

        except ImportError:
            logger.warning("Biopython not available. Using simple coordinate-based RMSD.")
            return PDBProcessor._compute_rmsd_simple(pdb_ref, pdb_mobile, selection)

    @staticmethod
    def _compute_rmsd_simple(pdb_ref: str, pdb_mobile: str, selection: str = "CA") -> float:
        """Simple RMSD calculation by parsing PDB coordinates directly."""
        def parse_coords(pdb_path):
            coords = []
            with open(pdb_path) as f:
                for line in f:
                    if line.startswith("ATOM"):
                        atom_name = line[12:16].strip()
                        if selection == "CA" and atom_name != "CA":
                            continue
                        try:
                            x = float(line[30:38])
                            y = float(line[38:46])
                            z = float(line[46:54])
                            coords.append([x, y, z])
                        except (ValueError, IndexError):
                            continue
            return np.array(coords)

        ref_coords = parse_coords(pdb_ref)
        mob_coords = parse_coords(pdb_mobile)

        n = min(len(ref_coords), len(mob_coords))
        if n < 3:
            return 0.0

        ref_coords = ref_coords[:n]
        mob_coords = mob_coords[:n]

        # Simple RMSD (no superposition)
        diff = ref_coords - mob_coords
        rmsd = np.sqrt(np.mean(np.sum(diff ** 2, axis=1)))
        return float(rmsd)

    @staticmethod
    def extract_confidence_scores(pdb_path: str) -> np.ndarray:
        """
        Extract per-residue pLDDT confidence scores from PDB B-factor column.

        AlphaFold stores per-residue pLDDT in the B-factor column (61-66)
        of ATOM records. This method extracts and averages them per residue.

        Args:
            pdb_path: Path to PDB file generated by AlphaFold.

        Returns:
            Numpy array of per-residue pLDDT scores (0-100 scale).
        """
        residue_scores = {}
        with open(pdb_path) as f:
            for line in f:
                if line.startswith("ATOM"):
                    try:
                        res_id = (line[21], line[22:26].strip(), line[17:20].strip())
                        b_factor = float(line[60:66].strip())
                        if res_id not in residue_scores:
                            residue_scores[res_id] = []
                        residue_scores[res_id].append(b_factor)
                    except (ValueError, IndexError):
                        continue

        if not residue_scores:
            return np.array([])

        # Average per-residue scores
        scores = [float(np.mean(v)) for v in residue_scores.values()]
        return np.array(scores)

    @staticmethod
    def convert_pdb_to_pdbqt(pdb_path: str, output_pdbqt: Optional[str] = None) -> str:
        """
        Convert PDB file to PDBQT format for AutoDock Vina.

        Uses prepare_receptor4.py from AutoDock Tools, with fallback
        to a simple conversion.

        Args:
            pdb_path: Input PDB file path.
            output_pdbqt: Output PDBQT path (auto-generated if None).

        Returns:
            Path to the generated PDBQT file.
        """
        pdb_path = Path(pdb_path)
        if output_pdbqt is None:
            output_pdbqt = str(pdb_path.with_suffix(".pdbqt"))

        # Try using prepare_receptor4.py
        try:
            subprocess.run(
                ["python", "prepare_receptor4.py",
                 "-r", str(pdb_path),
                 "-o", output_pdbqt,
                 "-A", "hydrogens"],
                capture_output=True, text=True, check=True, timeout=60
            )
            logger.info(f"PDBQT conversion complete: {output_pdbqt}")
            return output_pdbqt
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"prepare_receptor4.py failed: {e}")

        # Fallback: use obabel if available
        try:
            subprocess.run(
                ["obabel", str(pdb_path), "-O", output_pdbqt, "--gen3D"],
                capture_output=True, text=True, check=True, timeout=60
            )
            logger.info(f"OpenBabel PDBQT conversion: {output_pdbqt}")
            return output_pdbqt
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            logger.warning("OpenBabel not available for PDBQT conversion.")

        # Simple fallback: copy the file and add PDBQT header
        logger.warning("Using basic PDBQT conversion (no charges added). "
                       "Install Meeko or AutoDock Tools for better results.")
        with open(pdb_path) as f_in:
            content = f_in.read()
        with open(output_pdbqt, "w") as f_out:
            f_out.write("REMARK  Basic PDBQT conversion (no charges)\n")
            f_out.write(content)

        return output_pdbqt

    @staticmethod
    def visualize_structure(pdb_path: str, style: str = "stick") -> Optional[str]:
        """
        Generate an HTML visualization of the protein structure using py3Dmol.

        Args:
            pdb_path: Path to PDB file.
            style: Visualization style ('stick', 'cartoon', 'sphere', 'line').

        Returns:
            HTML string for 3D visualization, or None if py3Dmol unavailable.
        """
        try:
            import py3Dmol
            with open(pdb_path) as f:
                pdb_data = f.read()

            view = py3Dmol.view(width=600, height=400)
            view.addModel(pdb_data, "pdb")

            if style == "cartoon":
                view.setStyle({"cartoon": {"color": "spectrum"}})
            elif style == "sphere":
                view.setStyle({"sphere": {"colorscheme": "Chain"}})
            elif style == "line":
                view.setStyle({"line": {}})
            else:
                view.setStyle({"stick": {"colorscheme": "Chain"}})

            view.zoomTo()
            return view._make_html()
        except ImportError:
            logger.warning("py3Dmol not available. Install with: pip install py3Dmol")
            return None

    @staticmethod
    def validate_pdb(pdb_path: str) -> Tuple[bool, List[str]]:
        """
        Validate a PDB file for common issues.

        Args:
            pdb_path: Path to PDB file.

        Returns:
            Tuple of (is_valid, list_of_issues).
        """
        issues = []
        with open(pdb_path) as f:
            lines = f.readlines()

        atom_count = 0
        has_ter = False
        has_end = False
        chain_ids = set()

        for line in lines:
            if line.startswith("ATOM"):
                atom_count += 1
                if len(line) >= 22:
                    chain_ids.add(line[21])
                # Check for invalid coordinates
                try:
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    if any(np.isnan([x, y, z])):
                        issues.append(f"NaN coordinates at atom {atom_count}")
                except (ValueError, IndexError):
                    issues.append(f"Invalid coordinate format at line: {line[:50]}")
            elif line.startswith("TER"):
                has_ter = True
            elif line.startswith("END"):
                has_end = True

        if atom_count == 0:
            issues.append("No ATOM records found")
        if not has_end:
            issues.append("Missing END record")
        if len(chain_ids) > 1:
            issues.append(f"Multiple chains found: {chain_ids}")

        is_valid = len(issues) == 0
        return is_valid, issues

    @staticmethod
    def get_structure_metrics(pdb_path: str) -> Dict[str, Any]:
        """
        Compute comprehensive structure quality metrics.

        Args:
            pdb_path: Path to PDB file.

        Returns:
            Dictionary of structure metrics.
        """
        metrics = {
            "num_residues": 0,
            "num_chains": 0,
            "num_atoms": 0,
            "num_water": 0,
            "num_ligands": 0,
        }

        residues = set()
        chains = set()
        atoms = 0
        water = 0
        ligands = 0

        try:
            with open(pdb_path) as f:
                for line in f:
                    if line.startswith("ATOM"):
                        atoms += 1
                        try:
                            chain = line[21] if len(line) > 21 else ""
                            res_seq = line[22:26].strip()
                            res_name = line[17:20].strip()
                            residues.add((chain, res_seq))
                            chains.add(chain)
                        except IndexError:
                            pass
                    elif line.startswith("HETATM"):
                        res_name = line[17:20].strip() if len(line) > 20 else ""
                        if res_name == "HOH":
                            water += 1
                        else:
                            ligands += 1

            metrics["num_residues"] = len(residues)
            metrics["num_chains"] = len(chains)
            metrics["num_atoms"] = atoms
            metrics["num_water"] = water
            metrics["num_ligands"] = ligands

            # Extract pLDDT if available
            plddt_scores = PDBProcessor.extract_confidence_scores(pdb_path)
            if len(plddt_scores) > 0:
                metrics["mean_plddt"] = float(np.mean(plddt_scores))
                metrics["min_plddt"] = float(np.min(plddt_scores))
                metrics["max_plddt"] = float(np.max(plddt_scores))

            # Structural completeness
            if len(residues) > 0:
                metrics["completeness"] = min(100.0, atoms / (len(residues) * 10) * 100)

        except Exception as e:
            logger.error(f"Error computing structure metrics: {e}")

        return metrics

    @staticmethod
    def extract_binding_site(
        pdb_path: str,
        ligand_chain: str = "",
        ligand_resname: str = "",
        radius: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Extract binding site residues around a ligand.

        Args:
            pdb_path: Path to PDB file.
            ligand_chain: Chain ID of the ligand.
            ligand_resname: Residue name of the ligand.
            radius: Distance radius in Ångströms.

        Returns:
            Dictionary with binding site information.
        """
        import warnings
        binding_site = {
            "center": None,
            "residues": [],
            "num_residues": 0,
            "radius": radius,
        }

        try:
            # Parse ligand coordinates
            ligand_coords = []
            with open(pdb_path) as f:
                for line in f:
                    if line.startswith("HETATM"):
                        res_name = line[17:20].strip()
                        chain = line[21].strip() if len(line) > 21 else ""
                        if ((not ligand_resname or res_name == ligand_resname) and
                                (not ligand_chain or chain == ligand_chain)):
                            try:
                                x = float(line[30:38])
                                y = float(line[38:46])
                                z = float(line[46:54])
                                ligand_coords.append([x, y, z])
                            except (ValueError, IndexError):
                                continue

            if not ligand_coords:
                logger.warning("No ligand found for binding site detection")
                return binding_site

            ligand_center = np.mean(ligand_coords, axis=0)
            binding_site["center"] = ligand_center.tolist()

            # Find nearby residues
            nearby = []
            with open(pdb_path) as f:
                for line in f:
                    if line.startswith("ATOM"):
                        try:
                            x = float(line[30:38])
                            y = float(line[38:46])
                            z = float(line[46:54])
                            atom_coord = np.array([x, y, z])
                            dist = np.min(np.linalg.norm(
                                np.array(ligand_coords) - atom_coord, axis=1
                            ))
                            if dist <= radius:
                                chain = line[21] if len(line) > 21 else ""
                                res_seq = line[22:26].strip()
                                res_name = line[17:20].strip()
                                nearby.append({
                                    "chain": chain,
                                    "residue": res_seq,
                                    "name": res_name,
                                    "distance": float(dist),
                                })
                        except (ValueError, IndexError):
                            continue

            # Remove duplicates and sort
            unique_residues = {}
            for r in nearby:
                key = (r["chain"], r["residue"])
                if key not in unique_residues or r["distance"] < unique_residues[key]["distance"]:
                    unique_residues[key] = r

            binding_site["residues"] = sorted(
                unique_residues.values(), key=lambda x: x["distance"]
            )
            binding_site["num_residues"] = len(binding_site["residues"])

        except Exception as e:
            logger.error(f"Binding site detection error: {e}")

        return binding_site
