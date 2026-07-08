"""
Molecular Descriptor Module
============================

Advanced molecular descriptor calculation and drug-likeness filter module.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logger.warning("RDKit not available. Install with: conda install -c conda-forge rdkit")


# ──────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────


@dataclass
class FilterResult:
    """Drug-likeness filter result."""
    name: str
    passed: bool
    violations: List[str] = field(default_factory=list)
    score: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.passed


# ──────────────────────────────────────────────────────────
# Drug-likeness Filters
# ──────────────────────────────────────────────────────────


def lipinski_rule_of_five(mol: Chem.Mol) -> FilterResult:
    """
    Lipinski's Rule of Five for drug-likeness.

    Rules:
        - Molecular weight ≤ 500 Da
        - LogP ≤ 5
        - H-bond donors ≤ 5
        - H-bond acceptors ≤ 10

    Args:
        mol: RDKit Mol object.

    Returns:
        FilterResult with pass/fail and violation details.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return FilterResult(name="Lipinski Rule of Five", passed=False, violations=["RDKit unavailable"])

    violations = []
    details = {}

    mw = float(Descriptors.MolWt(mol))
    logp = float(Descriptors.MolLogP(mol))
    hbd = int(Descriptors.NumHDonors(mol))
    hba = int(Descriptors.NumHAcceptors(mol))

    details["MW"] = mw
    details["LogP"] = logp
    details["HBD"] = hbd
    details["HBA"] = hba

    if mw > 500:
        violations.append(f"MW > 500 ({mw:.1f})")
    if logp > 5:
        violations.append(f"LogP > 5 ({logp:.1f})")
    if hbd > 5:
        violations.append(f"HBD > 5 ({hbd})")
    if hba > 10:
        violations.append(f"HBA > 10 ({hba})")

    score = 4 - len(violations)
    return FilterResult(
        name="Lipinski Rule of Five",
        passed=len(violations) <= 1,
        violations=violations,
        score=score,
        details=details,
    )


def veber_rule(mol: Chem.Mol) -> FilterResult:
    """
    Veber's rule for oral bioavailability.

    Rules:
        - Rotatable bonds ≤ 10
        - TPSA ≤ 140 Å² (or ≤ 12 HBD + HBA)

    Args:
        mol: RDKit Mol object.

    Returns:
        FilterResult.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return FilterResult(name="Veber Rule", passed=False, violations=["RDKit unavailable"])

    violations = []
    details = {}

    rotb = int(Descriptors.NumRotatableBonds(mol))
    tpsa = float(Descriptors.TPSA(mol))

    details["RotatableBonds"] = rotb
    details["TPSA"] = tpsa

    if rotb > 10:
        violations.append(f"Rotatable bonds > 10 ({rotb})")
    if tpsa > 140:
        violations.append(f"TPSA > 140 ({tpsa:.1f})")

    score = 2 - len(violations)
    return FilterResult(
        name="Veber Rule",
        passed=len(violations) == 0,
        violations=violations,
        score=score,
        details=details,
    )


def ghose_filter(mol: Chem.Mol) -> FilterResult:
    """
    Ghose filter for drug-likeness.

    Rules:
        - MW: 160 to 480 Da
        - LogP: -0.4 to 5.6
        - Heavy atoms: 20 to 70
        - Molar refractivity: 40 to 130

    Args:
        mol: RDKit Mol object.

    Returns:
        FilterResult.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return FilterResult(name="Ghose Filter", passed=False, violations=["RDKit unavailable"])

    violations = []
    details = {}

    mw = float(Descriptors.MolWt(mol))
    logp = float(Descriptors.MolLogP(mol))
    heavy_atoms = int(Descriptors.HeavyAtomCount(mol))
    mr = float(Descriptors.MolMR(mol))

    details["MW"] = mw
    details["LogP"] = logp
    details["HeavyAtoms"] = heavy_atoms
    details["MolarRefractivity"] = mr

    if mw < 160 or mw > 480:
        violations.append(f"MW not in 160-480 ({mw:.1f})")
    if logp < -0.4 or logp > 5.6:
        violations.append(f"LogP not in -0.4~5.6 ({logp:.1f})")
    if heavy_atoms < 20 or heavy_atoms > 70:
        violations.append(f"Heavy atoms not in 20-70 ({heavy_atoms})")
    if mr < 40 or mr > 130:
        violations.append(f"Molar refractivity not in 40-130 ({mr:.1f})")

    return FilterResult(
        name="Ghose Filter",
        passed=len(violations) == 0,
        violations=violations,
        score=4 - len(violations),
        details=details,
    )


def lead_likeness_filter(mol: Chem.Mol) -> FilterResult:
    """
    Lead-likeness filter (for fragments suitable for optimization).

    Rules:
        - MW: 250 to 350 Da
        - LogP: 1 to 3
        - HBD ≤ 3
        - HBA ≤ 6
        - Rotatable bonds ≤ 8

    Args:
        mol: RDKit Mol object.

    Returns:
        FilterResult.
    """
    if not RDKIT_AVAILABLE or mol is None:
        return FilterResult(name="Lead-likeness", passed=False, violations=["RDKit unavailable"])

    violations = []
    details = {}

    mw = float(Descriptors.MolWt(mol))
    logp = float(Descriptors.MolLogP(mol))
    hbd = int(Descriptors.NumHDonors(mol))
    hba = int(Descriptors.NumHAcceptors(mol))
    rotb = int(Descriptors.NumRotatableBonds(mol))

    details["MW"] = mw
    details["LogP"] = logp
    details["HBD"] = hbd
    details["HBA"] = hba
    details["RotB"] = rotb

    if mw < 250 or mw > 350:
        violations.append(f"MW not in 250-350 ({mw:.1f})")
    if logp < 1 or logp > 3:
        violations.append(f"LogP not in 1-3 ({logp:.1f})")
    if hbd > 3:
        violations.append(f"HBD > 3 ({hbd})")
    if hba > 6:
        violations.append(f"HBA > 6 ({hba})")
    if rotb > 8:
        violations.append(f"RotB > 8 ({rotb})")

    return FilterResult(
        name="Lead-likeness",
        passed=len(violations) == 0,
        violations=violations,
        score=5 - len(violations),
        details=details,
    )


# ──────────────────────────────────────────────────────────
# Comprehensive Descriptor Calculator
# ──────────────────────────────────────────────────────────


class DescriptorCalculator:
    """
    Comprehensive molecular descriptor calculator.

    Organizes descriptors into categories:
    - 1D: Constitutional descriptors (atom counts, MW, formula)
    - 2D: Topological descriptors (connectivity, kappa, etc.)
    - 3D: Geometrical descriptors (requires conformers)
    - ADMET-related: Drug-likeness filters

    Usage:
        calc = DescriptorCalculator()
        all_desc = calc.calculate_all(mol)
        lipinski = calc.calculate_druglikeness(mol)
    """

    def __init__(self, include_3d: bool = False):
        self.include_3d = include_3d

    def calculate_all(self, mol: Chem.Mol) -> Dict[str, Any]:
        """Calculate all available descriptors."""
        if not RDKIT_AVAILABLE or mol is None:
            return {}
        descriptors = {}
        descriptors.update(self.calculate_1d(mol))
        descriptors.update(self.calculate_2d(mol))
        if self.include_3d:
            descriptors.update(self.calculate_3d(mol))
        return descriptors

    def calculate_1d(self, mol: Chem.Mol) -> Dict[str, Any]:
        """Calculate 1D (constitutional) descriptors."""
        if not RDKIT_AVAILABLE or mol is None:
            return {}
        return {
            "MW": float(Descriptors.MolWt(mol)),
            "ExactMW": float(Descriptors.ExactMolWt(mol)),
            "HeavyAtomMW": float(Descriptors.HeavyAtomMolWt(mol)),
            "Formula": str(Descriptors.MolecularFormula(mol)),
            "NumAtoms": mol.GetNumAtoms(),
            "NumHeavyAtoms": mol.GetNumHeavyAtoms(),
            "NumBonds": mol.GetNumBonds(),
            "NumHeteroatoms": int(Lipinski.NumHeteroatoms(mol)),
            "NumRadicalElectrons": int(Descriptors.NumRadicalElectrons(mol)),
            "NumValenceElectrons": int(Descriptors.NumValenceElectrons(mol)),
            "FormalCharge": int(Chem.GetFormalCharge(mol)),
            "HeavyAtomCount": int(Descriptors.HeavyAtomCount(mol)),
        }

    def calculate_2d(self, mol: Chem.Mol) -> Dict[str, Any]:
        """Calculate 2D (topological) descriptors."""
        if not RDKIT_AVAILABLE or mol is None:
            return {}
        return {
            "LogP": float(Descriptors.MolLogP(mol)),
            "LogD": float(Descriptors.MolLogP(mol)),  # Same as LogP at pH 7.4
            "TPSA": float(Descriptors.TPSA(mol)),
            "HBD": int(Descriptors.NumHDonors(mol)),
            "HBA": int(Descriptors.NumHAcceptors(mol)),
            "NHOH": int(Descriptors.NHOHCount(mol)),
            "NO": int(Descriptors.NOCount(mol)),
            "RotB": int(Descriptors.NumRotatableBonds(mol)),
            "RingCount": int(Lipinski.RingCount(mol)),
            "AromaticRings": int(Descriptors.NumAromaticRings(mol)),
            "AliphaticRings": int(Descriptors.NumAliphaticRings(mol)),
            "SaturatedRings": int(Descriptors.NumSaturatedRings(mol)),
            "FractionCSP3": float(Descriptors.FractionCsp3(mol)),
            "Chi0v": float(Descriptors.Chi0v(mol)),
            "Chi1v": float(Descriptors.Chi1v(mol)),
            "Kappa1": float(Descriptors.Kappa1(mol)),
            "Kappa2": float(Descriptors.Kappa2(mol)),
            "Kappa3": float(Descriptors.Kappa3(mol)),
            "HallKierAlpha": float(Descriptors.HallKierAlpha(mol)),
            "MolarRefractivity": float(Descriptors.MolMR(mol)),
            "MinPartialCharge": float(Descriptors.MinPartialCharge(mol)),
            "MaxPartialCharge": float(Descriptors.MaxPartialCharge(mol)),
        }

    def calculate_3d(self, mol: Chem.Mol) -> Dict[str, Any]:
        """Calculate 3D (geometrical) descriptors. Requires embedded conformer."""
        if not RDKIT_AVAILABLE or mol is None:
            return {}
        desc = {}
        try:
            if mol.GetNumConformers() > 0:
                desc["NumConformers"] = mol.GetNumConformers()
                # 3D descriptors could be added here
            else:
                desc["NumConformers"] = 0
        except Exception:
            desc["NumConformers"] = 0
        return desc

    def calculate_druglikeness(self, mol: Chem.Mol) -> Dict[str, Any]:
        """Calculate all drug-likeness filter results."""
        return {
            "lipinski": lipinski_rule_of_five(mol),
            "veber": veber_rule(mol),
            "ghose": ghose_filter(mol),
            "lead_likeness": lead_likeness_filter(mol),
        }

    @staticmethod
    def descriptor_names() -> List[str]:
        """Get list of all available descriptor names."""
        return [
            "MW", "ExactMW", "HeavyAtomMW", "Formula",
            "NumAtoms", "NumHeavyAtoms", "NumBonds", "NumHeteroatoms",
            "NumRadicalElectrons", "NumValenceElectrons", "FormalCharge",
            "HeavyAtomCount", "LogP", "LogD", "TPSA", "HBD", "HBA",
            "NHOH", "NO", "RotB", "RingCount", "AromaticRings",
            "AliphaticRings", "SaturatedRings", "FractionCSP3",
            "Chi0v", "Chi1v", "Kappa1", "Kappa2", "Kappa3",
            "HallKierAlpha", "MolarRefractivity",
            "MinPartialCharge", "MaxPartialCharge",
        ]


# ──────────────────────────────────────────────────────────
# Batch Processing
# ──────────────────────────────────────────────────────────


def batch_calculate(
    molecules: List[Chem.Mol],
    descriptors: Optional[List[str]] = None,
) -> "pd.DataFrame":
    """
    Calculate descriptors for a batch of molecules.

    Args:
        molecules: List of RDKit Mol objects.
        descriptors: List of descriptor names. If None, calculate all.

    Returns:
        pandas DataFrame with molecules as rows and descriptors as columns.
    """
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas is required for batch processing.")
        return None

    if not RDKIT_AVAILABLE:
        logger.error("RDKit is required.")
        return None

    calc = DescriptorCalculator()
    all_data = []

    for i, mol in enumerate(molecules):
        if mol is None:
            all_data.append({"mol_idx": i, "valid": False})
            continue

        data = {"mol_idx": i, "valid": True}
        desc_dict = calc.calculate_all(mol)

        if descriptors:
            for d in descriptors:
                data[d] = desc_dict.get(d, None)
        else:
            data.update(desc_dict)

        all_data.append(data)

    df = pd.DataFrame(all_data)

    # Add drug-likeness columns
    for i, mol in enumerate(molecules):
        if mol is not None:
            lipinski = lipinski_rule_of_five(mol)
            veber = veber_rule(mol)
            df.loc[i, "Lipinski_Pass"] = lipinski.passed
            df.loc[i, "Lipinski_Score"] = lipinski.score
            df.loc[i, "Veber_Pass"] = veber.passed

    return df
