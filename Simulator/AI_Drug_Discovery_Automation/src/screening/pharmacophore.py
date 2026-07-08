"""
Pharmacophore Module
====================

Pharmacophore-based virtual screening for identifying compounds
with specific pharmacophoric features (HBA, HBD, hydrophobic, aromatic, etc.).
"""

import logging
import math
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem
    from rdkit.Chem import ChemicalFeatures, rdMolDescriptors
    from rdkit.Chem.Pharm3D import Pharmacophore as Pharm3D
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logger.warning("RDKit not available. Install with: conda install -c conda-forge rdkit")


# ──────────────────────────────────────────────────────────
# Enums & Data Models
# ──────────────────────────────────────────────────────────


class FeatureType(Enum):
    """Pharmacophoric feature types."""
    HYDROGEN_BOND_ACCEPTOR = "hb_acceptor"
    HYDROGEN_BOND_DONOR = "hb_donor"
    HYDROPHOBIC = "hydrophobic"
    AROMATIC = "aromatic"
    POSITIVE_IONIZABLE = "positive"
    NEGATIVE_IONIZABLE = "negative"
    HALOGEN = "halogen"
    LIPO = "lipophilic"


@dataclass
class Feature:
    """A pharmacophoric feature with position and properties."""
    type: FeatureType
    position: Tuple[float, float, float]  # (x, y, z) coordinates
    radius: float = 1.0
    direction: Optional[Tuple[float, float, float]] = None
    weight: float = 1.0

    def distance_to(self, other: "Feature") -> float:
        """Euclidean distance to another feature."""
        return math.sqrt(
            (self.position[0] - other.position[0]) ** 2 +
            (self.position[1] - other.position[1]) ** 2 +
            (self.position[2] - other.position[2]) ** 2
        )

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "position": list(self.position),
            "radius": self.radius,
            "weight": self.weight,
        }


@dataclass
class Pharmacophore:
    """A complete pharmacophore model."""
    features: List[Feature] = field(default_factory=list)
    name: str = ""
    source: str = ""

    def add_feature(self, feature: Feature) -> None:
        self.features.append(feature)

    def remove_feature(self, index: int) -> None:
        if 0 <= index < len(self.features):
            self.features.pop(index)

    def num_features(self) -> Dict[str, int]:
        """Count features by type."""
        counts = {}
        for f in self.features:
            t = f.type.value
            counts[t] = counts.get(t, 0) + 1
        return counts

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "source": self.source,
            "features": [f.to_dict() for f in self.features],
            "feature_counts": self.num_features(),
        }

    def __len__(self) -> int:
        return len(self.features)


# ──────────────────────────────────────────────────────────
# Pharmacophore Generator
# ──────────────────────────────────────────────────────────


class PharmacophoreGenerator:
    """
    Generate pharmacophore models from molecular structures.

    Identifies pharmacophoric features: HBD, HBA, hydrophobic,
    aromatic, positive/negative ionizable groups.

    Usage:
        gen = PharmacophoreGenerator()
        pharm = gen.generate_from_smiles("CC(=O)Oc1ccccc1C(=O)O")
        print(pharm.num_features())
    """

    def __init__(self, use_rdkit_feature_factory: bool = True):
        self.use_rdkit = use_rdkit_feature_factory and RDKIT_AVAILABLE
        if self.use_rdkit:
            try:
                self.feature_factory = ChemicalFeatures.BuildFeatureFactory()
            except Exception:
                logger.warning("RDKit feature factory not available, using internal rules.")
                self.use_rdkit = False

    def generate_from_mol(self, mol: Chem.Mol) -> Pharmacophore:
        """
        Generate a pharmacophore model from an RDKit Mol object.

        Args:
            mol: RDKit Mol object (must have 3D conformer).

        Returns:
            Pharmacophore model with identified features.
        """
        if not RDKIT_AVAILABLE or mol is None:
            return Pharmacophore(name="empty")

        pharm = Pharmacophore(name="generated")
        pharm.source = "mol"

        if self.use_rdkit and mol.GetNumConformers() > 0:
            # Use RDKit's feature factory
            try:
                feats = self.feature_factory.GetFeaturesForMol(mol)
                for feat in feats:
                    family = feat.GetFamily()
                    pos = feat.GetPos()
                    position = (pos.x, pos.y, pos.z)

                    feature_type = self._map_family_to_type(family)
                    if feature_type:
                        pharm.add_feature(Feature(
                            type=feature_type,
                            position=position,
                            radius=1.0,
                        ))
            except Exception as e:
                logger.warning(f"RDKit feature extraction failed: {e}")
                self._add_rule_based_features(mol, pharm)
        else:
            # Use rule-based feature detection
            self._add_rule_based_features(mol, pharm)

        return pharm

    def generate_from_smiles(self, smiles: str) -> Pharmacophore:
        """
        Generate a pharmacophore model from a SMILES string.

        Args:
            smiles: SMILES string.

        Returns:
            Pharmacophore model (may be empty if no 3D coords).
        """
        if not RDKIT_AVAILABLE:
            return Pharmacophore(name="empty")

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            logger.warning(f"Invalid SMILES: {smiles}")
            return Pharmacophore(name="invalid")

        # Try to generate 3D coordinates
        try:
            from rdkit.Chem import AllChem
            mol_with_H = Chem.AddHs(mol)
            params = AllChem.ETKDGv3()
            params.randomSeed = 42
            result = AllChem.EmbedMolecule(mol_with_H, params)
            if result == 0:
                mol = mol_with_H
        except Exception:
            pass

        return self.generate_from_mol(mol)

    def _map_family_to_type(self, family: str) -> Optional[FeatureType]:
        """Map RDKit feature family to our FeatureType."""
        mapping = {
            "Donor": FeatureType.HYDROGEN_BOND_DONOR,
            "Acceptor": FeatureType.HYDROGEN_BOND_ACCEPTOR,
            "Hydrophobe": FeatureType.HYDROPHOBIC,
            "LumpedHydrophobe": FeatureType.HYDROPHOBIC,
            "Aromatic": FeatureType.AROMATIC,
            "PosIonizable": FeatureType.POSITIVE_IONIZABLE,
            "NegIonizable": FeatureType.NEGATIVE_IONIZABLE,
            "ZnBinder": FeatureType.HYDROGEN_BOND_ACCEPTOR,
            "Halogen": FeatureType.HALOGEN,
        }
        return mapping.get(family)

    def _add_rule_based_features(self, mol: Chem.Mol, pharm: Pharmacophore) -> None:
        """Add features based on SMARTS patterns."""
        patterns = {
            FeatureType.HYDROGEN_BOND_ACCEPTOR: Chem.MolFromSmarts("[!$([#1,#6])]"),
            FeatureType.HYDROGEN_BOND_DONOR: Chem.MolFromSmarts("[!H0!#1]"),
            FeatureType.HYDROPHOBIC: Chem.MolFromSmarts("[$([C,c]);!$(C=O)]"),
            FeatureType.AROMATIC: Chem.MolFromSmarts("[a]"),
            FeatureType.POSITIVE_IONIZABLE: Chem.MolFromSmarts("[N;!H0]"),
            FeatureType.NEGATIVE_IONIZABLE: Chem.MolFromSmarts("[O,S;!H0]"),
        }

        for feat_type, pattern in patterns.items():
            if pattern:
                matches = mol.GetSubstructMatches(pattern)
                for match in matches:
                    atom_idx = match[0] if isinstance(match, tuple) else match
                    atom = mol.GetAtomWithIdx(atom_idx)
                    if mol.GetNumConformers() > 0:
                        conf = mol.GetConformer()
                        pos = conf.GetAtomPosition(atom_idx)
                        pharm.add_feature(Feature(
                            type=feat_type,
                            position=(pos.x, pos.y, pos.z),
                            radius=1.0,
                        ))

        logger.info(f"Added {len(pharm.features)} rule-based features")


# ──────────────────────────────────────────────────────────
# Pharmacophore Matcher
# ──────────────────────────────────────────────────────────


class PharmacophoreMatcher:
    """
    Match pharmacophore models against compound libraries.

    Uses geometric hashing and distance-based matching
    to identify compounds that satisfy the pharmacophore.

    Usage:
        matcher = PharmacophoreMatcher()
        score = matcher.match(query_pharm, target_pharm)
        hits = matcher.screen_library(query_pharm, compounds)
    """

    def __init__(self, tolerance: float = 1.0, min_features: int = 3):
        """
        Initialize the pharmacophore matcher.

        Args:
            tolerance: Distance tolerance in Ångströms.
            min_features: Minimum number of matched features.
        """
        self.tolerance = tolerance
        self.min_features = min_features

    def match(
        self,
        query: Pharmacophore,
        target: Pharmacophore,
    ) -> float:
        """
        Match two pharmacophore models and return a score.

        Score is based on the fraction of query features matched
        within the distance tolerance.

        Args:
            query: Query pharmacophore.
            target: Target pharmacophore.

        Returns:
            Match score (0 = no match, 1 = perfect match).
        """
        if len(query.features) == 0:
            return 0.0

        matched = 0
        for qf in query.features:
            for tf in target.features:
                if qf.type == tf.type:
                    dist = qf.distance_to(tf)
                    if dist <= self.tolerance:
                        matched += 1
                        break

        # Score based on matched fraction with feature weighting
        total_weight = sum(f.weight for f in query.features)
        matched_weight = sum(
            qf.weight for qf in query.features
            if any(
                qf.type == tf.type and qf.distance_to(tf) <= self.tolerance
                for tf in target.features
            )
        )

        score = matched_weight / total_weight if total_weight > 0 else 0.0
        return float(score)

    def screen_library(
        self,
        query: Pharmacophore,
        compounds: List[Any],
        threshold: float = 0.5,
    ) -> List[Tuple[Any, float]]:
        """
        Screen a compound library against a pharmacophore query.

        Args:
            query: Query pharmacophore model.
            compounds: List of compounds (must have pharmacophore or be SMILES).
            threshold: Minimum score threshold.

        Returns:
            List of (compound, score) tuples sorted by score.
        """
        results = []
        gen = PharmacophoreGenerator()

        for compound in compounds:
            if isinstance(compound, str):
                # SMILES string
                target_pharm = gen.generate_from_smiles(compound)
            elif isinstance(compound, Pharmacophore):
                target_pharm = compound
            else:
                continue

            score = self.match(query, target_pharm)
            if score >= threshold:
                results.append((compound, score))

        results.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Pharmacophore screen: {len(results)} hits (threshold={threshold})")
        return results

    def feature_match_matrix(
        self,
        query: Pharmacophore,
        target: Pharmacophore,
    ) -> np.ndarray:
        """
        Compute the pairwise distance matrix between features.

        Args:
            query: Query pharmacophore.
            target: Target pharmacophore.

        Returns:
            NxM matrix of distances (query features × target features).
        """
        matrix = np.zeros((len(query.features), len(target.features)))
        for i, qf in enumerate(query.features):
            for j, tf in enumerate(target.features):
                matrix[i, j] = qf.distance_to(tf)
        return matrix
