"""
Drug-likeness Filters Module
============================

Various drug-likeness and ADMET filters for compound screening.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from src.molecular.descriptors import (
    lipinski_rule_of_five as _lipinski,
    veber_rule as _veber,
    ghose_filter as _ghose,
    FilterResult as _FilterResult,
)

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


# ──────────────────────────────────────────────────────────
# Data Model
# ──────────────────────────────────────────────────────────


@dataclass
class FilterResult:
    """Result of a drug-likeness filter check."""
    name: str
    passed: bool
    violations: List[str] = field(default_factory=list)
    score: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.passed

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "violations": self.violations,
            "score": self.score,
            "details": self.details,
        }


# ──────────────────────────────────────────────────────────
# Individual Filters
# ──────────────────────────────────────────────────────────


class LipinskiFilter:
    """
    Lipinski's Rule of Five filter.

    Rules:
        - Molecular weight ≤ 500 Da
        - LogP ≤ 5
        - H-bond donors ≤ 5
        - H-bond acceptors ≤ 10

    A compound is considered drug-like if it violates ≤ 1 rule.
    """

    def __init__(self):
        self.name = "Lipinski Rule of Five"

    def check(self, mol) -> FilterResult:
        if not RDKIT_AVAILABLE or mol is None:
            return FilterResult(name=self.name, passed=True, violations=["RDKit unavailable"])

        result = _lipinski(mol)
        return FilterResult(
            name=self.name,
            passed=result.passed,
            violations=result.violations,
            score=result.score,
            details=result.details,
        )

    def check_batch(self, molecules) -> List[FilterResult]:
        return [self.check(m) for m in molecules]

    def violations(self, mol) -> List[str]:
        return self.check(mol).violations


class VeberFilter:
    """
    Veber's rule for oral bioavailability.

    Rules:
        - Rotatable bonds ≤ 10
        - TPSA ≤ 140 Å² (or sum HBD/HBA ≤ 12)
    """

    def __init__(self):
        self.name = "Veber Rule"

    def check(self, mol) -> FilterResult:
        if not RDKIT_AVAILABLE or mol is None:
            return FilterResult(name=self.name, passed=True)
        result = _veber(mol)
        return FilterResult(
            name=self.name,
            passed=result.passed,
            violations=result.violations,
            score=result.score,
            details=result.details,
        )

    def check_batch(self, molecules) -> List[FilterResult]:
        return [self.check(m) for m in molecules]


class GhoseFilter:
    """
    Ghose filter for drug-likeness.

    Rules:
        - MW: 160 to 480 Da
        - LogP: -0.4 to 5.6
        - Heavy atoms: 20 to 70
        - Molar refractivity: 40 to 130
    """

    def __init__(self):
        self.name = "Ghose Filter"

    def check(self, mol) -> FilterResult:
        if not RDKIT_AVAILABLE or mol is None:
            return FilterResult(name=self.name, passed=True)
        result = _ghose(mol)
        return FilterResult(
            name=self.name,
            passed=result.passed,
            violations=result.violations,
            score=result.score,
            details=result.details,
        )

    def check_batch(self, molecules) -> List[FilterResult]:
        return [self.check(m) for m in molecules]


class PfizerRule:
    """
    Pfizer's rule for toxicity warning.

    Rule:
        - If LogP > 3 and TPSA < 75, alert for toxicity
    """

    def __init__(self):
        self.name = "Pfizer Rule"

    def check(self, mol) -> FilterResult:
        if not RDKIT_AVAILABLE or mol is None:
            return FilterResult(name=self.name, passed=True)

        violations = []
        details = {}

        logp = float(Descriptors.MolLogP(mol))
        tpsa = float(Descriptors.TPSA(mol))
        details["LogP"] = logp
        details["TPSA"] = tpsa

        passed = True
        if logp > 3 and tpsa < 75:
            violations.append(f"LogP={logp:.1f} > 3 and TPSA={tpsa:.1f} < 75 - toxicity risk")
            passed = False

        return FilterResult(
            name=self.name,
            passed=passed,
            violations=violations,
            score=1 if passed else 0,
            details=details,
        )


class GoldenTriangle:
    """
    Golden Triangle rule for good oral bioavailability.

    Rule:
        - LogD (LogP) between 1 and 4
        - TPSA between 20 and 130 Å²
    """

    def __init__(self):
        self.name = "Golden Triangle"

    def check(self, mol) -> FilterResult:
        if not RDKIT_AVAILABLE or mol is None:
            return FilterResult(name=self.name, passed=True)

        violations = []
        details = {}

        logp = float(Descriptors.MolLogP(mol))
        tpsa = float(Descriptors.TPSA(mol))
        mw = float(Descriptors.MolWt(mol))
        details["LogP"] = logp
        details["TPSA"] = tpsa
        details["MW"] = mw

        in_triangle = (1 <= logp <= 4) and (20 <= tpsa <= 130)
        if not in_triangle:
            violations.append(f"Outside Golden Triangle (LogP={logp:.1f}, TPSA={tpsa:.1f})")

        return FilterResult(
            name=self.name,
            passed=in_triangle,
            violations=violations,
            score=1 if in_triangle else 0,
            details=details,
        )


# ──────────────────────────────────────────────────────────
# Combined Filter
# ──────────────────────────────────────────────────────────


class ADMETEnsembleFilter:
    """
    Comprehensive ADMET filter combining multiple rules.

    Applies all filters and returns aggregate results.

    Usage:
        filter = ADMETEnsembleFilter()
        result = filter.check_all(mol)
        if filter.aggregate_pass(mol):
            print("Passes all filters")
    """

    def __init__(self):
        self.lipinski = LipinskiFilter()
        self.veber = VeberFilter()
        self.ghose = GhoseFilter()
        self.pfizer = PfizerRule()
        self.golden = GoldenTriangle()

    def check_all(self, mol) -> Dict[str, FilterResult]:
        """Apply all filters to a molecule."""
        return {
            "lipinski": self.lipinski.check(mol),
            "veber": self.veber.check(mol),
            "ghose": self.ghose.check(mol),
            "pfizer": self.pfizer.check(mol),
            "golden_triangle": self.golden.check(mol),
        }

    def aggregate_pass(self, mol, require: List[str] = None) -> bool:
        """
        Check if molecule passes all (or specified) filters.

        Args:
            mol: RDKit Mol object.
            require: List of filter names to require. If None, require all.

        Returns:
            True if passes all required filters.
        """
        results = self.check_all(mol)

        if require is None:
            require = ["lipinski", "veber", "ghose"]

        return all(results[f].passed for f in require if f in results)

    def aggregate_score(self, mol) -> int:
        """Get aggregate filter score (number of filters passed)."""
        results = self.check_all(mol)
        return sum(1 for r in results.values() if r.passed)

    def filter_library(self, compounds, require: List[str] = None) -> list:
        """
        Filter a compound library, keeping only those that pass.

        Args:
            compounds: List of RDKit Mol objects or SMILES strings.
            require: List of filter names to require.

        Returns:
            List of compounds that pass all required filters.
        """
        passed = []
        for cpd in compounds:
            if isinstance(cpd, str):
                mol = Chem.MolFromSmiles(cpd) if RDKIT_AVAILABLE else None
            else:
                mol = cpd

            if mol and self.aggregate_pass(mol, require):
                passed.append(cpd)

        logger.info(f"ADMET ensemble filter: {len(passed)}/{len(compounds)} passed")
        return passed

    def report(self, mol) -> Dict[str, Any]:
        """Generate a comprehensive filter report for a molecule."""
        results = self.check_all(mol)
        return {
            "molecule": {
                "MW": Descriptors.MolWt(mol) if RDKIT_AVAILABLE else 0,
                "LogP": Descriptors.MolLogP(mol) if RDKIT_AVAILABLE else 0,
                "TPSA": Descriptors.TPSA(mol) if RDKIT_AVAILABLE else 0,
            },
            "filters": {k: v.to_dict() for k, v in results.items()},
            "aggregate_pass": self.aggregate_pass(mol),
            "aggregate_score": self.aggregate_score(mol),
        }
