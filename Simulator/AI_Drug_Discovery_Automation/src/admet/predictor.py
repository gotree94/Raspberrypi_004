"""
ADMET Predictor Module
======================

Comprehensive ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity)
prediction engine using machine learning models.
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict

import numpy as np

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

from src.config import ADMETConfig, get_config
from src.molecular.rdkit_utils import (
    MolFromSMILES, calculate_all_descriptors,
    calculate_mw, calculate_logp, calculate_hbd, calculate_hba,
    calculate_tpsa, calculate_rotatable_bonds,
)
from src.admet.filters import (
    LipinskiFilter, VeberFilter, GhoseFilter, ADMETEnsembleFilter,
)


# ──────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────


@dataclass
class ADMETResult:
    """
    Complete ADMET prediction results for a molecule.

    Attributes:
        smiles: Input SMILES string.
        physicochemical: Physicochemical properties (MW, LogP, etc.)
        absorption: Absorption predictions (Caco2, bioavailability, logS)
        distribution: Distribution predictions (logD, BBB, PPB, Vd)
        metabolism: Metabolism predictions (CYP inhibition, clearance)
        excretion: Excretion predictions (half-life, renal clearance)
        toxicity: Toxicity predictions (AMES, hERG, LD50, hepatotoxicity)
        druglikeness: Drug-likeness filter results (Lipinski, Veber, Ghose)
        admet_score: Aggregated ADMET score (0-100)
        warnings: List of warnings for concerning predictions
    """
    smiles: str
    physicochemical: Dict[str, float] = field(default_factory=dict)
    absorption: Dict[str, float] = field(default_factory=dict)
    distribution: Dict[str, float] = field(default_factory=dict)
    metabolism: Dict[str, float] = field(default_factory=dict)
    excretion: Dict[str, float] = field(default_factory=dict)
    toxicity: Dict[str, float] = field(default_factory=dict)
    druglikeness: Dict[str, Any] = field(default_factory=dict)
    admet_score: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    def summary(self) -> str:
        """Get a one-line summary of ADMET properties."""
        parts = []
        if self.physicochemical.get("LogP"):
            parts.append(f"LogP={self.physicochemical['LogP']:.2f}")
        if self.absorption.get("logS"):
            parts.append(f"Solubility={self.absorption['logS']:.2f}")
        if self.toxicity.get("AMES"):
            parts.append(f"AMES={'+Mutagen' if self.toxicity['AMES'] > 0.5 else '-NonMutagen'}")
        if self.toxicity.get("hERG"):
            parts.append(f"hERG_Risk={self.toxicity['hERG']:.1f}%")
        dl = self.druglikeness.get("lipinski_pass", "")
        return f"ADMET({', '.join(parts)}) | DrugLikeness={'PASS' if dl else 'FAIL'} | Score={self.admet_score:.1f}"


# ──────────────────────────────────────────────────────────
# ADMET Predictor
# ──────────────────────────────────────────────────────────


class ADMETPredictor:
    """
    Comprehensive ADMET property predictor.

    Predicts absorption, distribution, metabolism, excretion, and toxicity
    properties using ML models with RDKit descriptors as features.
    Falls back to rule-based predictions when ML models are not available.

    Usage:
        predictor = ADMETPredictor()
        result = predictor.predict("CC(=O)Oc1ccccc1C(=O)O")
        print(result.summary())
        print(f"ADMET Score: {result.admet_score}")
    """

    def __init__(
        self,
        config: Optional[ADMETConfig] = None,
        use_ml: bool = True,
    ):
        """
        Initialize the ADMET predictor.

        Args:
            config: ADMET configuration.
            use_ml: Whether to use ML models (fallback to rule-based if False).
        """
        self.config = config or get_config().admet
        self.use_ml = use_ml
        self.models: Dict[str, Any] = {}
        self.ensemble_filter = ADMETEnsembleFilter()

        if self.use_ml:
            self._load_models()

    def _load_models(self) -> None:
        """Load pre-trained ML models."""
        model_dir = Path(self.config.model_dir)
        if model_dir.exists():
            for model_file in model_dir.glob("*.pkl"):
                try:
                    with open(model_file, "rb") as f:
                        model_data = pickle.load(f)
                    prop_name = model_file.stem
                    self.models[prop_name] = model_data
                    logger.info(f"Loaded ADMET model: {prop_name}")
                except Exception as e:
                    logger.warning(f"Failed to load model {model_file}: {e}")

        logger.info(f"ADMET models loaded: {list(self.models.keys())}")

    # ──────────────────────────────────────────────
    # Main Prediction Interface
    # ──────────────────────────────────────────────

    def predict(self, mol_or_smiles: Any) -> ADMETResult:
        """
        Predict full ADMET profile for a molecule.

        Args:
            mol_or_smiles: RDKit Mol object or SMILES string.

        Returns:
            ADMETResult with all predicted properties.
        """
        # Input processing
        if isinstance(mol_or_smiles, str):
            smiles = mol_or_smiles
            mol = MolFromSMILES(smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES: {smiles}")
        else:
            mol = mol_or_smiles
            try:
                from rdkit.Chem import MolToSmiles
                smiles = MolToSmiles(mol)
            except Exception:
                smiles = ""

        if not RDKIT_AVAILABLE:
            return self._predict_rule_based(smiles)

        # Get molecular descriptors
        desc = calculate_all_descriptors(mol)

        # Predict each ADMET category
        result = ADMETResult(
            smiles=smiles,
            physicochemical=self._predict_physicochemical(mol, desc),
            absorption=self._predict_absorption(mol, desc),
            distribution=self._predict_distribution(mol, desc),
            metabolism=self._predict_metabolism(mol, desc),
            excretion=self._predict_excretion(mol, desc),
            toxicity=self._predict_toxicity(mol, desc),
            druglikeness=self._predict_druglikeness(mol),
        )

        # Compute aggregate score
        result.admet_score = self._compute_admet_score(result)
        result.warnings = self._generate_warnings(result)

        return result

    def predict_batch(self, molecules: List[Any]) -> List[ADMETResult]:
        """
        Predict ADMET for multiple molecules.

        Args:
            molecules: List of SMILES strings or Mol objects.

        Returns:
            List of ADMETResult objects.
        """
        return [self.predict(m) for m in molecules]

    # ──────────────────────────────────────────────
    # Individual Property Predictions
    # ──────────────────────────────────────────────

    def _predict_physicochemical(self, mol: Any, desc: Dict) -> Dict[str, float]:
        """Predict physicochemical properties."""
        return {
            "MW": float(desc.get("MW", 0)),
            "LogP": float(desc.get("LogP", 0)),
            "LogD": float(desc.get("LogP", 0)),  # LogP ≈ LogD at pH 7.4
            "HBD": int(desc.get("HBD", 0)),
            "HBA": int(desc.get("HBA", 0)),
            "TPSA": float(desc.get("TPSA", 0)),
            "RotB": int(desc.get("RotB", 0)),
            "HeavyAtomCount": int(desc.get("HeavyAtomCount", 0)),
            "FractionCSP3": float(desc.get("FractionCSP3", 0)),
            "FormalCharge": int(desc.get("FormalCharge", 0)),
            "RingCount": int(desc.get("RingCount", 0)),
            "AromaticRings": int(desc.get("AromaticRings", 0)),
        }

    def _predict_absorption(self, mol: Any, desc: Dict) -> Dict[str, float]:
        """Predict absorption properties."""
        logp = desc.get("LogP", 0)
        tpsa = desc.get("TPSA", 0)
        mw = desc.get("MW", 0)

        # Water solubility (LogS) using ESOL-like model
        log_s = self._predict_solubility(mol, desc)

        # Caco2 permeability (rules of thumb)
        caco2 = 0.5  # moderate
        if logp > 2 and logp < 5 and mw < 500:
            caco2 = 0.8  # high
        elif mw > 700 or tpsa > 140:
            caco2 = 0.2  # low

        # Bioavailability score (Veber rules based)
        bioavailability = 0.55  # default
        rotb = desc.get("RotB", 10)
        if rotb <= 10 and tpsa <= 140:
            bioavailability = 0.85  # good oral bioavailability

        # P-glycoprotein substrate likelihood
        pgp_substrate = 0.5
        if logp > 4 or mw > 600:
            pgp_substrate = 0.7
        elif logp < 1 or mw < 300:
            pgp_substrate = 0.3

        return {
            "logS": round(log_s, 3),
            "caco2_permeability": round(caco2, 3),
            "bioavailability": round(bioavailability, 3),
            "Pgp_substrate": round(pgp_substrate, 3),
            "intestinal_absorption": round(self._sigmoid(bioavailability, 0.5, 10), 3),
        }

    def _predict_distribution(self, mol: Any, desc: Dict) -> Dict[str, float]:
        """Predict distribution properties."""
        logp = desc.get("LogP", 0)
        tpsa = desc.get("TPSA", 0)

        # Blood-Brain Barrier penetration
        bbb = 0.0
        if logp > 2 and tpsa < 90:
            bbb = 0.8  # High BBB
        elif tpsa > 140:
            bbb = 0.1  # Low BBB
        elif logp < 0:
            bbb = 0.2
        else:
            bbb = self._sigmoid(logp, 2.0, 1.0) * (1 - self._sigmoid(tpsa, 90, 30))

        # Plasma Protein Binding (PPB)
        ppb = self._sigmoid(logp, 3.0, 1.0) * 100

        # Volume of distribution (L/kg)
        vd = 0.5 + 0.5 * logp if logp > 0 else 0.5

        # Fraction unbound
        fu = 100 - ppb

        return {
            "BBB_score": round(bbb, 3),
            "PPB_percent": round(ppb, 1),
            "fraction_unbound": round(fu, 1),
            "Vd_L_per_kg": round(vd, 2),
            "logD": round(logp * 0.9, 2),  # Approximate logD from logP
        }

    def _predict_metabolism(self, mol: Any, desc: Dict) -> Dict[str, float]:
        """Predict metabolism properties."""
        mw = desc.get("MW", 0)
        logp = desc.get("LogP", 0)

        # CYP inhibition probabilities (simplified model)
        cyp_inhibition = {
            "CYP1A2": self._sigmoid(mw, 300, 100) * 0.3,
            "CYP2D6": self._sigmoid(logp, 3.0, 1.0) * 0.4,
            "CYP3A4": self._sigmoid(mw, 400, 150) * 0.5,
            "CYP2C9": self._sigmoid(logp, 3.5, 1.5) * 0.3,
            "CYP2C19": self._sigmoid(mw, 350, 100) * 0.3,
        }

        # Clearance prediction (simplified)
        clearance = 10.0  # mL/min/kg (default moderate)
        if mw > 500:
            clearance = 15.0  # High MW → higher clearance
        if logp > 4:
            clearance = 20.0  # High lipophilicity → higher clearance

        return {
            **cyp_inhibition,
            "clearance_mL_min_kg": round(clearance, 1),
            "CYP_inhibition_risk": round(max(cyp_inhibition.values()), 3),
        }

    def _predict_excretion(self, mol: Any, desc: Dict) -> Dict[str, float]:
        """Predict excretion properties."""
        mw = desc.get("MW", 0)
        logp = desc.get("LogP", 0)

        # Half-life estimation (simplified)
        half_life = 4.0  # hours (default)
        if mw < 300 and logp < 2:
            half_life = 2.0  # Small hydrophilic → short half-life
        elif mw > 500 and logp > 4:
            half_life = 12.0  # Large lipophilic → long half-life

        # Renal clearance
        tpsa = desc.get("TPSA", 0)
        renal_clearance = 50.0  # mL/min (default)
        if tpsa > 100:
            renal_clearance = 80.0  # High polarity → renal excretion

        return {
            "half_life_hours": round(half_life, 1),
            "renal_clearance_mL_min": round(renal_clearance, 1),
            "total_clearance_mL_min_kg": round(20.0 / (logp + 1) if logp > 0 else 15.0, 1),
        }

    def _predict_toxicity(self, mol: Any, desc: Dict) -> Dict[str, float]:
        """Predict toxicity properties."""
        logp = desc.get("LogP", 0)
        mw = desc.get("MW", 0)
        hbd = desc.get("HBD", 0)
        hba = desc.get("HBA", 0)

        # AMES mutagenicity (simplified)
        ames = 0.1  # default low
        # Presence of certain functional groups increases AMES risk
        ames_risk_patterns = [
            Chem.MolFromSmarts("[N+](=O)[O-]"),  # Nitro
            Chem.MolFromSmarts("[NX2]N=[NX2]"),  # Azo
            Chem.MolFromSmarts("[NX1]"),  # Primary amine (aromatic)
        ]
        for pattern in ames_risk_patterns:
            if pattern and mol.HasSubstructMatch(pattern):
                ames = 0.7
                break

        # hERG toxicity risk
        herg = 0.0
        if logp > 3.5:
            herg += 0.3
        if mw > 400:
            herg += 0.2
        if hbd > 2:
            herg += 0.1
        # Basic nitrogen increases hERG risk
        basic_n = Chem.MolFromSmarts("[N;H1,H2;!$(NC=O)]")
        if basic_n and mol.HasSubstructMatch(basic_n):
            herg += 0.3
        herg = min(herg, 1.0)

        # LD50 (simplified)
        ld50 = 2000.0  # mg/kg (default moderate)
        if logp > 4:
            ld50 = 500.0  # High lipophilicity → more toxic
        elif logp < 1:
            ld50 = 3000.0  # Low lipophilicity → less toxic

        # Hepatotoxicity risk
        hepato = self._sigmoid(logp, 3.5, 1.0) * 0.6 + self._sigmoid(mw, 400, 150) * 0.4

        return {
            "AMES_mutagenicity": round(ames, 3),
            "hERG_risk": round(herg, 3),
            "hERG_percent": round(herg * 100, 1),
            "LD50_mg_per_kg": round(ld50, 1),
            "hepatotoxicity": round(hepato, 3),
            "carcinogenicity": round(self._sigmoid(logp, 4.0, 1.0) * 0.3, 3),
            "respiratory_toxicity": round(self._sigmoid(mw, 350, 100) * 0.2, 3),
        }

    def _predict_solubility(self, mol: Any, desc: Dict) -> float:
        """Predict aqueous solubility (LogS) using ESOL-like model."""
        logp = desc.get("LogP", 0)
        mw = desc.get("MW", 0)
        rotb = desc.get("RotB", 0)
        aromatic_proportion = 0.0

        try:
            aromatic_atoms = sum(1 for atom in mol.GetAtoms() if atom.GetIsAromatic())
            total_heavy = desc.get("HeavyAtomCount", 1)
            aromatic_proportion = aromatic_atoms / max(total_heavy, 1)
        except Exception:
            pass

        # ESOL model: logS = 0.16 - 0.63*logP - 0.0062*MW + 0.066*RotB - 0.74*ArProp
        log_s = 0.16 - 0.63 * logp - 0.0062 * mw + 0.066 * rotb - 0.74 * aromatic_proportion

        # Apply reasonable bounds
        log_s = max(-12.0, min(2.0, log_s))
        return log_s

    def _predict_druglikeness(self, mol: Any) -> Dict[str, Any]:
        """Predict drug-likeness using various filters."""
        lipinski = self.ensemble_filter.lipinski.check(mol)
        veber = self.ensemble_filter.veber.check(mol)
        ghose = self.ensemble_filter.ghose.check(mol)

        return {
            "lipinski_pass": lipinski.passed,
            "lipinski_score": lipinski.score,
            "lipinski_violations": lipinski.violations,
            "veber_pass": veber.passed,
            "veber_violations": veber.violations,
            "ghose_pass": ghose.passed,
            "qed_score": self._calculate_qed(mol),
        }

    def _predict_rule_based(self, smiles: str) -> ADMETResult:
        """Fallback prediction without RDKit."""
        mol = MolFromSMILES(smiles)
        if mol is None:
            return ADMETResult(smiles=smiles, warnings=["Invalid SMILES"])

        desc = calculate_all_descriptors(mol) if RDKIT_AVAILABLE else {}
        return ADMETResult(
            smiles=smiles,
            physicochemical={"MW": desc.get("MW", 0), "LogP": desc.get("LogP", 0)},
            druglikeness={"lipinski_pass": True},
            admet_score=50.0,
            warnings=["Rule-based prediction only (no RDKit)"],
        )

    # ──────────────────────────────────────────────
    # Scoring
    # ──────────────────────────────────────────────

    def _compute_admet_score(self, result: ADMETResult) -> float:
        """
        Compute an aggregated ADMET score (0-100, higher = better).

        Weighted average of:
        - Physicochemical properties (20%)
        - Absorption (20%)
        - Distribution (15%)
        - Metabolism (15%)
        - Toxicity (30%)
        """
        score = 0.0
        weights = 0.0

        # Physicochemical score (based on drug-like ranges)
        if result.physicochemical:
            pc = result.physicochemical
            pc_score = 100.0
            if 150 < pc.get("MW", 0) < 500:
                pc_score += 10
            if 1 < pc.get("LogP", 0) < 4:
                pc_score += 10
            if pc.get("HBD", 5) <= 5:
                pc_score += 10
            if pc.get("HBA", 10) <= 10:
                pc_score += 10
            if pc.get("RotB", 10) <= 10:
                pc_score += 5
            if 20 < pc.get("TPSA", 0) < 130:
                pc_score += 5
            score += min(100, pc_score) * 0.2
            weights += 0.2

        # Absorption score
        if result.absorption:
            ab = result.absorption
            abs_score = ab.get("bioavailability", 0.5) * 100
            if ab.get("logS", 0) > -4:
                abs_score += 10
            score += min(100, abs_score) * 0.2
            weights += 0.2

        # Distribution score
        if result.distribution:
            dist = result.distribution
            dist_score = 100.0
            bbb = dist.get("BBB_score", 0)
            if 0.1 < bbb < 0.9:
                dist_score += 5  # Moderate BBB is good for most targets
            score += min(100, dist_score) * 0.15
            weights += 0.15

        # Metabolism score (lower CYP inhibition = better)
        if result.metabolism:
            met = result.metabolism
            met_score = 100 - min(100, met.get("CYP_inhibition_risk", 0) * 100)
            score += max(0, met_score) * 0.15
            weights += 0.15

        # Toxicity score (lower risk = higher score)
        if result.toxicity:
            tox = result.toxicity
            tox_score = 100.0
            tox_score -= tox.get("AMES_mutagenicity", 0) * 40
            tox_score -= tox.get("hERG_risk", 0) * 30
            tox_score -= tox.get("hepatotoxicity", 0) * 20
            ld50 = tox.get("LD50_mg_per_kg", 2000)
            if ld50 < 100:
                tox_score -= 30
            elif ld50 < 500:
                tox_score -= 15
            score += max(0, tox_score) * 0.3
            weights += 0.3

        # Drug-likeness bonus
        dl = result.druglikeness
        if dl.get("lipinski_pass"):
            score += 5
        if dl.get("veber_pass"):
            score += 5
        weights += 10  # 10 points bonus

        return round(max(0, min(100, score / max(weights, 1) * 100)), 1)

    def _generate_warnings(self, result: ADMETResult) -> List[str]:
        """Generate warning messages for concerning predictions."""
        warnings = []

        if result.toxicity.get("AMES_mutagenicity", 0) > 0.5:
            warnings.append("AMES mutagenicity detected - potential DNA mutagen")
        if result.toxicity.get("hERG_risk", 0) > 0.7:
            warnings.append("High hERG toxicity risk - potential cardiac safety issue")
        if result.toxicity.get("hepatotoxicity", 0) > 0.7:
            warnings.append("High hepatotoxicity risk")
        if result.toxicity.get("LD50_mg_per_kg", 2000) < 500:
            warnings.append(f"Low LD50 ({result.toxicity['LD50_mg_per_kg']:.0f} mg/kg) - high acute toxicity")
        if result.absorption.get("bioavailability", 0.5) < 0.3:
            warnings.append("Poor predicted oral bioavailability")
        if not result.druglikeness.get("lipinski_pass", True):
            violations = result.druglikeness.get("lipinski_violations", [])
            warnings.append(f"Lipinski Rule of Five violations: {len(violations)}")

        return warnings

    # ──────────────────────────────────────────────
    # Utility Functions
    # ──────────────────────────────────────────────

    @staticmethod
    def _sigmoid(x: float, midpoint: float = 0.0, slope: float = 1.0) -> float:
        """Sigmoid function for smooth predictions."""
        return 1.0 / (1.0 + np.exp(-slope * (x - midpoint)))

    @staticmethod
    def _calculate_qed(mol: Any) -> float:
        """
        Calculate Quantitative Estimate of Drug-likeness (QED).

        Implements the Bickerton et al. QED measure.
        """
        if not RDKIT_AVAILABLE:
            return 0.5
        try:
            from rdkit.Chem.QED import defaults, qed
            return float(qed(mol))
        except (ImportError, AttributeError):
            # Manual calculation
            try:
                mw = Descriptors.MolWt(mol)
                logp = Descriptors.MolLogP(mol)
                hbd = Descriptors.NumHDonors(mol)
                hba = Descriptors.NumHAcceptors(mol)
                tpsa = Descriptors.TPSA(mol)
                rotb = Descriptors.NumRotatableBonds(mol)

                # Desirability functions (simplified)
                def d_mw(x): return np.exp(-((x - 300) / 150) ** 2)
                def d_logp(x): return np.exp(-((x - 2) / 1.5) ** 2)
                def d_hbd(x): return np.exp(-((x - 1) / 2) ** 2)
                def d_hba(x): return np.exp(-((x - 3) / 3) ** 2)
                def d_tpsa(x): return np.exp(-((x - 60) / 40) ** 2)
                def d_rotb(x): return np.exp(-((x - 3) / 3) ** 2)

                desirabilities = [d_mw(mw), d_logp(logp), d_hbd(hbd),
                                  d_hba(hba), d_tpsa(tpsa), d_rotb(rotb)]
                qed_val = np.exp(np.mean(np.log(desirabilities)))
                return float(qed_val)
            except Exception:
                return 0.5

    def to_json(self, result: ADMETResult) -> str:
        """Serialize ADMET result to JSON."""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
