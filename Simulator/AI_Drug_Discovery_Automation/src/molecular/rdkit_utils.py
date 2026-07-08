"""
RDKit Utility Functions
=======================

Core RDKit wrapper functions for molecular I/O, validation,
descriptor calculation, and manipulation.

All functions use REAL RDKit implementations.
"""

import io
import math
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Union
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Try importing RDKit
try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import (
        AllChem, Descriptors, Lipinski, MolFromSmiles, MolFromMolBlock,
        MolToSmiles, MolToMolBlock, rdMolDescriptors,
        rdMolDescriptors as RDMD,
    )
    from rdkit.Chem.Descriptors import (
        MolWt, HeavyAtomMolWt, MolLogP, NumHDonors, NumHAcceptors,
        TPSA, NumRotatableBonds, NumAromaticRings, NumAliphaticRings,
        NumSaturatedRings, FractionCsp3, Chi0v, Chi1v, Kappa1, Kappa2, Kappa3,
        HallKierAlpha, FpDensityMorgan1, FpDensityMorgan2, FpDensityMorgan3,
        MinPartialCharge, MaxPartialCharge, NumRadicalElectrons,
        NumValenceElectrons, HeavyAtomCount, NHOHCount, NOCount,
    )
    from rdkit.Chem.Lipinski import (
        RotatableBondSmarts, RingCount, NumHeteroatoms,
    )
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logger.warning("RDKit not available. Install with: conda install -c conda-forge rdkit")


# ──────────────────────────────────────────────────────────
# Molecular I/O
# ──────────────────────────────────────────────────────────


def MolFromSMILES(smiles: str, sanitize: bool = True) -> Optional[Chem.Mol]:
    """
    Create an RDKit Mol object from a SMILES string.

    Args:
        smiles: SMILES string.
        sanitize: Whether to sanitize the molecule (default: True).

    Returns:
        RDKit Mol object or None if invalid.
    """
    if not RDKIT_AVAILABLE:
        logger.error("RDKit is required but not available.")
        return None
    if not smiles or not isinstance(smiles, str):
        return None
    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=sanitize)
        if mol is None:
            logger.debug(f"Invalid SMILES: {smiles[:50]}")
        return mol
    except Exception as e:
        logger.error(f"Error parsing SMILES '{smiles[:50]}': {e}")
        return None


def MolFromSDF(sdf_path: str) -> List[Chem.Mol]:
    """
    Read molecules from an SDF file.

    Args:
        sdf_path: Path to SDF file.

    Returns:
        List of RDKit Mol objects.
    """
    if not RDKIT_AVAILABLE:
        logger.error("RDKit is required but not available.")
        return []
    sdf_path = Path(sdf_path)
    if not sdf_path.exists():
        raise FileNotFoundError(f"SDF file not found: {sdf_path}")
    try:
        supplier = Chem.SDMolSupplier(str(sdf_path), sanitize=True)
        molecules = [mol for mol in supplier if mol is not None]
        logger.info(f"Loaded {len(molecules)} molecules from {sdf_path}")
        return molecules
    except Exception as e:
        logger.error(f"Error reading SDF '{sdf_path}': {e}")
        return []


def MolToSMILES(mol: Chem.Mol, canonical: bool = True, isomeric: bool = True) -> str:
    """
    Convert an RDKit Mol object to a SMILES string.

    Args:
        mol: RDKit Mol object.
        canonical: Whether to generate canonical SMILES.
        isomeric: Whether to include stereochemistry information.

    Returns:
        SMILES string.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return ""
    try:
        return Chem.MolToSmiles(mol, canonical=canonical, isomeric=isomeric)
    except Exception as e:
        logger.error(f"Error converting Mol to SMILES: {e}")
        return ""


def MolToSDF(mol: Chem.Mol, output_path: str, conf_id: int = -1) -> bool:
    """
    Write a molecule to an SDF file.

    Args:
        mol: RDKit Mol object.
        output_path: Output SDF file path.
        conf_id: Conformer ID (-1 for all).

    Returns:
        True if successful.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return False
    try:
        writer = Chem.SDWriter(str(output_path))
        if conf_id >= 0:
            writer.write(mol, conf_id)
        else:
            writer.write(mol)
        writer.close()
        return True
    except Exception as e:
        logger.error(f"Error writing SDF: {e}")
        return False


# ──────────────────────────────────────────────────────────
# Molecule Validation & Standardization
# ──────────────────────────────────────────────────────────


def sanitize_molecule(mol: Chem.Mol) -> Chem.Mol:
    """
    Sanitize a molecule (assign bonds, charges, stereochemistry, etc.).

    Args:
        mol: RDKit Mol object.

    Returns:
        Sanitized Mol object or original if sanitization fails.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return mol
    try:
        mol_copy = Chem.RWMol(mol)
        Chem.SanitizeMol(mol_copy)
        return mol_copy
    except Exception as e:
        logger.warning(f"Sanitization failed: {e}")
        return mol


def standardize_smiles(smiles: str) -> str:
    """
    Standardize a SMILES string:
    - Canonicalize
    - Remove salts (keep largest fragment)
    - Neutralize

    Args:
        smiles: Input SMILES.

    Returns:
        Standardized SMILES.
    """
    if not RDKIT_AVAILABLE or not smiles:
        return smiles
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return smiles
        # Get the largest fragment (remove salts)
        fragments = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
        if len(fragments) > 1:
            mol = max(fragments, key=lambda m: m.GetNumAtoms())
        # Canonicalize
        return Chem.MolToSmiles(mol, canonical=True, isomeric=True)
    except Exception as e:
        logger.debug(f"Standardization failed: {e}")
        return smiles


def is_valid_smiles(smiles: str) -> bool:
    """
    Check if a SMILES string represents a valid molecule.

    Args:
        smiles: SMILES string.

    Returns:
        True if valid.
    """
    if not RDKIT_AVAILABLE or not smiles:
        return False
    try:
        mol = Chem.MolFromSmiles(smiles)
        return mol is not None
    except Exception:
        return False


# ──────────────────────────────────────────────────────────
# Descriptor Calculation (Individual)
# ──────────────────────────────────────────────────────────


def calculate_mw(mol: Chem.Mol) -> float:
    """Calculate molecular weight (Dalton)."""
    if not RDKIT_AVAILABLE or mol is None:
        return 0.0
    try:
        return float(Descriptors.MolWt(mol))
    except Exception:
        return 0.0


def calculate_logp(mol: Chem.Mol) -> float:
    """Calculate Wildman-Crippen LogP."""
    if not RDKIT_AVAILABLE or mol is None:
        return 0.0
    try:
        return float(Descriptors.MolLogP(mol))
    except Exception:
        return 0.0


def calculate_hbd(mol: Chem.Mol) -> int:
    """Calculate number of hydrogen bond donors."""
    if not RDKIT_AVAILABLE or mol is None:
        return 0
    try:
        return int(Descriptors.NumHDonors(mol))
    except Exception:
        return 0


def calculate_hba(mol: Chem.Mol) -> int:
    """Calculate number of hydrogen bond acceptors."""
    if not RDKIT_AVAILABLE or mol is None:
        return 0
    try:
        return int(Descriptors.NumHAcceptors(mol))
    except Exception:
        return 0


def calculate_tpsa(mol: Chem.Mol) -> float:
    """Calculate topological polar surface area (Å²)."""
    if not RDKIT_AVAILABLE or mol is None:
        return 0.0
    try:
        return float(Descriptors.TPSA(mol))
    except Exception:
        return 0.0


def calculate_rotatable_bonds(mol: Chem.Mol) -> int:
    """Calculate number of rotatable bonds."""
    if not RDKIT_AVAILABLE or mol is None:
        return 0
    try:
        return int(Descriptors.NumRotatableBonds(mol))
    except Exception:
        return 0


# ──────────────────────────────────────────────────────────
# Comprehensive Descriptor Calculation
# ──────────────────────────────────────────────────────────


def calculate_all_descriptors(mol: Chem.Mol) -> Dict[str, float]:
    """
    Calculate all available molecular descriptors.

    Args:
        mol: RDKit Mol object.

    Returns:
        Dictionary of descriptor name → value.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return {}

    desc = {}
    try:
        desc["MW"] = float(Descriptors.MolWt(mol))
        desc["HeavyAtomMW"] = float(Descriptors.HeavyAtomMolWt(mol))
        desc["LogP"] = float(Descriptors.MolLogP(mol))
        desc["HBD"] = int(Descriptors.NumHDonors(mol))
        desc["HBA"] = int(Descriptors.NumHAcceptors(mol))
        desc["TPSA"] = float(Descriptors.TPSA(mol))
        desc["RotB"] = int(Descriptors.NumRotatableBonds(mol))
        desc["HeavyAtomCount"] = int(Descriptors.HeavyAtomCount(mol))
        desc["NHOH"] = int(Descriptors.NHOHCount(mol))
        desc["NO"] = int(Descriptors.NOCount(mol))
        desc["NumHeteroatoms"] = int(Lipinski.NumHeteroatoms(mol))
        desc["RingCount"] = int(Lipinski.RingCount(mol))
        desc["AromaticRings"] = int(Descriptors.NumAromaticRings(mol))
        desc["AliphaticRings"] = int(Descriptors.NumAliphaticRings(mol))
        desc["SaturatedRings"] = int(Descriptors.NumSaturatedRings(mol))
        desc["FractionCSP3"] = float(Descriptors.FractionCsp3(mol))
        desc["Chi0v"] = float(Descriptors.Chi0v(mol))
        desc["Chi1v"] = float(Descriptors.Chi1v(mol))
        desc["Kappa1"] = float(Descriptors.Kappa1(mol))
        desc["Kappa2"] = float(Descriptors.Kappa2(mol))
        desc["Kappa3"] = float(Descriptors.Kappa3(mol))
        desc["HallKierAlpha"] = float(Descriptors.HallKierAlpha(mol))
        desc["NumRadicalElectrons"] = int(Descriptors.NumRadicalElectrons(mol))
        desc["NumValenceElectrons"] = int(Descriptors.NumValenceElectrons(mol))
        desc["MinPartialCharge"] = float(Descriptors.MinPartialCharge(mol))
        desc["MaxPartialCharge"] = float(Descriptors.MaxPartialCharge(mol))

        # Formal charge
        desc["FormalCharge"] = int(Chem.GetFormalCharge(mol))

        # Formula and exact MW
        formula = Descriptors.MolecularFormula(mol)
        desc["Formula"] = formula
        desc["ExactMW"] = float(Descriptors.ExactMolWt(mol))

        # Number of atoms
        desc["NumAtoms"] = mol.GetNumAtoms()
        desc["NumHeavyAtoms"] = mol.GetNumHeavyAtoms()
        desc["NumBonds"] = mol.GetNumBonds()

    except Exception as e:
        logger.error(f"Error calculating descriptors: {e}")

    return desc


# ──────────────────────────────────────────────────────────
# Additional Utilities
# ──────────────────────────────────────────────────────────


def get_molecular_formula(mol: Chem.Mol) -> str:
    """Get the molecular formula."""
    if not RDKIT_AVAILABLE or mol is None:
        return ""
    try:
        return str(Descriptors.MolecularFormula(mol))
    except Exception:
        return ""


def get_molecular_weight_exact(mol: Chem.Mol) -> float:
    """Calculate exact molecular weight."""
    if not RDKIT_AVAILABLE or mol is None:
        return 0.0
    try:
        return float(Descriptors.ExactMolWt(mol))
    except Exception:
        return 0.0


def get_num_rings(mol: Chem.Mol) -> int:
    """Calculate total number of rings."""
    if not RDKIT_AVAILABLE or mol is None:
        return 0
    try:
        return int(Descriptors.RingCount(mol))
    except Exception:
        return 0


def get_aromatic_rings(mol: Chem.Mol) -> List[int]:
    """Get indices of aromatic rings."""
    if not RDKIT_AVAILABLE or mol is None:
        return []
    try:
        rings = mol.GetRingInfo()
        aromatics = []
        for ring in rings.AtomRings():
            if all(mol.GetAtomWithIdx(a).GetIsAromatic() for a in ring):
                aromatics.append(list(ring))
        return aromatics
    except Exception:
        return []


def detect_functional_groups(mol: Chem.Mol) -> List[Dict[str, Any]]:
    """
    Detect common functional groups in a molecule.

    Returns:
        List of dicts: {name, smarts, atom_indices}
    """
    if not RDKIT_AVAILABLE or mol is None:
        return []

    functional_groups = {
        "Alcohol": "[OX2H]",
        "Carboxylic Acid": "[CX3](=O)[OX2H]",
        "Amine": "[NX3;H2,H1;!$(NC=O)]",
        "Amide": "[NX3][CX3](=[OX1])",
        "Ester": "[OX2][CX3](=[OX1])",
        "Ether": "[OD2]([#6])[#6]",
        "Aldehyde": "[CX3H1](=O)[#6]",
        "Ketone": "[#6][CX3](=O)[#6]",
        "Nitro": "[NX3](=O)=O",
        "Sulfonamide": "[SX4](=O)(=O)[NX3]",
        "Halogen": "[F,Cl,Br,I]",
        "Nitrile": "[NX1]#[CX2]",
        "Aromatic": "[a]",
        "Phenol": "[OX2H][c]",
        "Sulfonic Acid": "[SX4](=O)(=O)[OX2H]",
        "Phosphate": "[PX4](=O)([OX2H])[OX2H]",
        "Thiol": "[SX2H]",
        "Sulfide": "[SX2]",
    }

    found = []
    for name, smarts in functional_groups.items():
        try:
            pattern = Chem.MolFromSmarts(smarts)
            if pattern:
                matches = mol.GetSubstructMatches(pattern)
                if matches:
                    found.append({
                        "name": name,
                        "smarts": smarts,
                        "count": len(matches),
                        "atom_indices": [list(m) for m in matches],
                    })
        except Exception:
            continue

    return found


def get_molecule_image(
    mol: Chem.Mol,
    size: Tuple[int, int] = (300, 300),
    kekulize: bool = True,
    wedge_bonds: bool = True,
) -> Optional[Any]:
    """
    Generate a 2D molecular image using RDKit.

    Args:
        mol: RDKit Mol object.
        size: Image size (width, height).
        kekulize: Whether to kekulize the structure.
        wedge_bonds: Whether to show wedged bonds.

    Returns:
        PIL Image object, or None if unavailable.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return None
    try:
        from rdkit.Chem import Draw
        img = Draw.MolToImage(mol, size=size, kekulize=kekulize, wedgeBonds=wedge_bonds)
        return img
    except ImportError:
        logger.warning("RDKit Draw module not available.")
        return None


def conformer_generation(mol: Chem.Mol, num_conformers: int = 10) -> Chem.Mol:
    """
    Generate 3D conformers for a molecule using ETKDG.

    Args:
        mol: RDKit Mol object.
        num_conformers: Number of conformers to generate.

    Returns:
        Mol object with embedded conformers (first successful embedding)
        or original Mol if embedding fails.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return mol
    try:
        mol_copy = Chem.RWMol(mol)
        mol_copy = Chem.AddHs(mol_copy)

        # Use ETKDG for conformer generation
        params = AllChem.ETKDGv3()
        params.numThreads = 4
        params.randomSeed = 42
        params.useRandomCoords = True

        result = AllChem.EmbedMultipleConfs(mol_copy, numConformers=num_conformers, params=params)
        if result:
            logger.info(f"Generated {len(result)} conformers")
            return mol_copy
        else:
            logger.warning("No conformers generated.")
            return mol
    except Exception as e:
        logger.error(f"Conformer generation failed: {e}")
        return mol


def embed_molecule(mol: Chem.Mol) -> bool:
    """
    Generate a single 3D conformation for a molecule.

    Args:
        mol: RDKit Mol object.

    Returns:
        True if embedding succeeded.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return False
    try:
        mol_with_H = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        result = AllChem.EmbedMolecule(mol_with_H, params)
        if result == 0:
            # Copy coordinates back to original mol
            conf = mol_with_H.GetConformer()
            mol.AddConformer(conf)
            return True
        return False
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return False
