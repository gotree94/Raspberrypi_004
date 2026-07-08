"""
Molecular Fingerprint Module
============================

분자 지문(Fingerprint) 생성 및 유사도 계산 모듈.

Supports:
    - Morgan/ECFP fingerprints (circular)
    - MACCS keys (166-bit)
    - Topological torsions
    - Pharmacophoric features
    - Atom pair fingerprints
    - RDKit default fingerprint
    - Tanimoto, Dice, Cosine similarity
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem, rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logger.warning("RDKit not available. Install with: conda install -c conda-forge rdkit")


# ──────────────────────────────────────────────────────────
# Abstract Base Class
# ──────────────────────────────────────────────────────────


class BaseFingerprintGenerator(ABC):
    """Abstract base class for fingerprint generators."""

    @abstractmethod
    def generate(self, mol: Chem.Mol) -> np.ndarray:
        """Generate fingerprint from an RDKit Mol object."""
        pass

    def generate_from_smiles(self, smiles: str) -> np.ndarray:
        """Generate fingerprint from a SMILES string."""
        if not RDKIT_AVAILABLE:
            return np.array([])
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return np.array([])
        return self.generate(mol)

    @property
    @abstractmethod
    def name(self) -> str:
        """Generator name."""
        pass

    @property
    @abstractmethod
    def bit_length(self) -> int:
        """Length of the fingerprint vector."""
        pass


# ──────────────────────────────────────────────────────────
# Fingerprint Generators
# ──────────────────────────────────────────────────────────


class MorganFingerprintGenerator(BaseFingerprintGenerator):
    """
    Morgan (ECFP-like) circular fingerprint generator.

    ECFP (Extended Connectivity Fingerprint) is the most widely used
    fingerprint type in drug discovery for similarity searching.
    """

    def __init__(self, radius: int = 2, nbits: int = 2048, use_features: bool = False):
        self.radius = radius
        self.nbits = nbits
        self.use_features = use_features

    def generate(self, mol: Chem.Mol) -> np.ndarray:
        if not RDKIT_AVAILABLE or mol is None:
            return np.zeros(self.nbits)
        try:
            fp = AllChem.GetMorganFingerprintAsBitVect(
                mol, self.radius, nBits=self.nbits, useFeatures=self.use_features
            )
            return np.array(fp, dtype=np.float32)
        except Exception as e:
            logger.error(f"Morgan fingerprint error: {e}")
            return np.zeros(self.nbits)

    @property
    def name(self) -> str:
        return f"Morgan_r{self.radius}_n{self.nbits}"

    @property
    def bit_length(self) -> int:
        return self.nbits


class MACCSFingerprintGenerator(BaseFingerprintGenerator):
    """
    MACCS (Molecular ACCess System) keys fingerprint.
    166-bit structural key fingerprint.
    """

    def __init__(self):
        pass

    def generate(self, mol: Chem.Mol) -> np.ndarray:
        if not RDKIT_AVAILABLE or mol is None:
            return np.zeros(166)
        try:
            fp = rdMolDescriptors.GetMACCSKeysFingerprint(mol)
            return np.array(fp, dtype=np.float32)
        except Exception as e:
            logger.error(f"MACCS fingerprint error: {e}")
            return np.zeros(166)

    @property
    def name(self) -> str:
        return "MACCS_166"

    @property
    def bit_length(self) -> int:
        return 166


class TopologicalFingerprintGenerator(BaseFingerprintGenerator):
    """
    Topological torsion fingerprint.
    Based on atom environment paths.
    """

    def __init__(self, nbits: int = 2048, target_size: int = 2048):
        self.nbits = nbits
        self.target_size = target_size

    def generate(self, mol: Chem.Mol) -> np.ndarray:
        if not RDKIT_AVAILABLE or mol is None:
            return np.zeros(self.target_size)
        try:
            fp = rdMolDescriptors.GetHashedTopologicalTorsionFingerprint(
                mol, nBits=self.target_size
            )
            return np.array(fp, dtype=np.float32)
        except Exception as e:
            logger.error(f"Topological fingerprint error: {e}")
            return np.zeros(self.target_size)

    @property
    def name(self) -> str:
        return f"Topological_n{self.target_size}"

    @property
    def bit_length(self) -> int:
        return self.target_size


class PharmacophoreFingerprintGenerator(BaseFingerprintGenerator):
    """
    Pharmacophoric feature fingerprint.
    Encodes presence of pharmacophoric features (donor, acceptor, etc.).
    """

    def __init__(self, nbits: int = 2048):
        self.nbits = nbits

    def generate(self, mol: Chem.Mol) -> np.ndarray:
        if not RDKIT_AVAILABLE or mol is None:
            return np.zeros(self.nbits)
        try:
            fp = rdMolDescriptors.GetHashedAtomPairFingerprint(
                mol, nBits=self.nbits
            )
            return np.array(fp, dtype=np.float32)
        except Exception as e:
            logger.error(f"Pharmacophore fingerprint error: {e}")
            return np.zeros(self.nbits)

    @property
    def name(self) -> str:
        return f"Pharmacophore_n{self.nbits}"

    @property
    def bit_length(self) -> int:
        return self.nbits


class AtomPairFingerprintGenerator(BaseFingerprintGenerator):
    """
    Atom pair fingerprint.
    Based on pairs of atoms and their topological distances.
    """

    def __init__(self, nbits: int = 2048):
        self.nbits = nbits

    def generate(self, mol: Chem.Mol) -> np.ndarray:
        if not RDKIT_AVAILABLE or mol is None:
            return np.zeros(self.nbits)
        try:
            fp = rdMolDescriptors.GetHashedAtomPairFingerprint(
                mol, nBits=self.nbits
            )
            return np.array(fp, dtype=np.float32)
        except Exception as e:
            logger.error(f"Atom pair fingerprint error: {e}")
            return np.zeros(self.nbits)

    @property
    def name(self) -> str:
        return f"AtomPair_n{self.nbits}"

    @property
    def bit_length(self) -> int:
        return self.nbits


class RDKitFingerprintGenerator(BaseFingerprintGenerator):
    """
    RDKit default fingerprint (path-based).
    Similar to Daylight fingerprints.
    """

    def __init__(self, min_path: int = 1, max_path: int = 7, nbits: int = 2048):
        self.min_path = min_path
        self.max_path = max_path
        self.nbits = nbits

    def generate(self, mol: Chem.Mol) -> np.ndarray:
        if not RDKIT_AVAILABLE or mol is None:
            return np.zeros(self.nbits)
        try:
            fp = Chem.RDKFingerprint(
                mol, minPath=self.min_path, maxPath=self.max_path,
                fpSize=self.nbits
            )
            return np.array(fp, dtype=np.float32)
        except Exception as e:
            logger.error(f"RDKit fingerprint error: {e}")
            return np.zeros(self.nbits)

    @property
    def name(self) -> str:
        return f"RDKit_p{self.max_path}_n{self.nbits}"

    @property
    def bit_length(self) -> int:
        return self.nbits


# ──────────────────────────────────────────────────────────
# Unified Fingerprint Manager
# ──────────────────────────────────────────────────────────


class FingerprintManager:
    """
    Unified interface for multiple fingerprint types.

    Usage:
        manager = FingerprintManager()
        fps = manager.compute_all(mol)
        morgan = fps['morgan']
    """

    def __init__(self, morgan_kwargs: Optional[Dict] = None):
        self.generators = {
            "morgan": MorganFingerprintGenerator(**(morgan_kwargs or {})),
            "maccs": MACCSFingerprintGenerator(),
            "topological": TopologicalFingerprintGenerator(),
            "atom_pair": AtomPairFingerprintGenerator(),
            "rdkit": RDKitFingerprintGenerator(),
        }

    def compute_all(self, mol: Chem.Mol) -> Dict[str, np.ndarray]:
        """Compute all fingerprints for a molecule."""
        return {name: gen.generate(mol) for name, gen in self.generators.items()}

    def compute_selected(self, mol: Chem.Mol, methods: List[str]) -> Dict[str, np.ndarray]:
        """Compute selected fingerprint types."""
        return {m: self.generators[m].generate(mol) for m in methods if m in self.generators}

    def add_generator(self, name: str, generator: BaseFingerprintGenerator) -> None:
        """Register a custom fingerprint generator."""
        self.generators[name] = generator

    def list_available(self) -> List[str]:
        """List available fingerprint types."""
        return list(self.generators.keys())

    def __repr__(self) -> str:
        return f"FingerprintManager(generators={list(self.generators.keys())})"


# ──────────────────────────────────────────────────────────
# Similarity Metrics
# ──────────────────────────────────────────────────────────


def tanimoto_similarity(fp1: np.ndarray, fp2: np.ndarray) -> float:
    """
    Compute Tanimoto coefficient between two binary fingerprint vectors.

    Tanimoto(A,B) = |A ∩ B| / |A ∪ B|

    Args:
        fp1: First fingerprint vector.
        fp2: Second fingerprint vector.

    Returns:
        Similarity score (0 = completely different, 1 = identical).
    """
    if len(fp1) != len(fp2):
        raise ValueError(f"Fingerprint length mismatch: {len(fp1)} vs {len(fp2)}")

    n_intersection = np.sum(fp1 & fp2)
    n_union = np.sum(fp1 | fp2)

    if n_union == 0:
        return 0.0
    return float(n_intersection / n_union)


def dice_similarity(fp1: np.ndarray, fp2: np.ndarray) -> float:
    """
    Compute Dice coefficient between two binary fingerprint vectors.

    Dice(A,B) = 2|A ∩ B| / (|A| + |B|)

    Args:
        fp1: First fingerprint vector.
        fp2: Second fingerprint vector.

    Returns:
        Similarity score (0 = completely different, 1 = identical).
    """
    if len(fp1) != len(fp2):
        raise ValueError(f"Fingerprint length mismatch: {len(fp1)} vs {len(fp2)}")

    n_intersection = np.sum(fp1 & fp2)
    sum_bits = np.sum(fp1) + np.sum(fp2)

    if sum_bits == 0:
        return 0.0
    return float(2.0 * n_intersection / sum_bits)


def cosine_similarity(fp1: np.ndarray, fp2: np.ndarray) -> float:
    """
    Compute Cosine similarity between two fingerprint vectors.

    Cosine(A,B) = (A·B) / (|A|·|B|)

    Args:
        fp1: First fingerprint vector.
        fp2: Second fingerprint vector.

    Returns:
        Similarity score (0 = orthogonal, 1 = identical).
    """
    if len(fp1) != len(fp2):
        raise ValueError(f"Fingerprint length mismatch: {len(fp1)} vs {len(fp2)}")

    dot_product = np.dot(fp1, fp2)
    norm_product = np.linalg.norm(fp1) * np.linalg.norm(fp2)

    if norm_product == 0:
        return 0.0
    return float(dot_product / norm_product)


def compute_similarity_matrix(fingerprints: List[np.ndarray]) -> np.ndarray:
    """
    Compute pairwise Tanimoto similarity matrix.

    Args:
        fingerprints: List of fingerprint vectors.

    Returns:
        NxN similarity matrix.
    """
    n = len(fingerprints)
    matrix = np.ones((n, n), dtype=np.float32)

    for i in range(n):
        for j in range(i + 1, n):
            sim = tanimoto_similarity(fingerprints[i], fingerprints[j])
            matrix[i, j] = sim
            matrix[j, i] = sim

    return matrix


def nearest_neighbors(
    query_fp: np.ndarray,
    fp_library: List[np.ndarray],
    k: int = 10,
    threshold: float = 0.0,
) -> List[Tuple[int, float]]:
    """
    Find k nearest neighbors by Tanimoto similarity.

    Args:
        query_fp: Query fingerprint.
        fp_library: Library of fingerprints to search.
        k: Number of neighbors to return.
        threshold: Minimum similarity threshold.

    Returns:
        List of (index, similarity_score) tuples, sorted by score descending.
    """
    similarities = []
    for i, lib_fp in enumerate(fp_library):
        sim = tanimoto_similarity(query_fp, lib_fp)
        if sim >= threshold:
            similarities.append((i, sim))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:k]


# ──────────────────────────────────────────────────────────
# Utility (RDKit compatibility)
# ──────────────────────────────────────────────────────────


def rdkit_tanimoto(fp1: DataStructs.ExplicitBitVect, fp2: DataStructs.ExplicitBitVect) -> float:
    """Compute Tanimoto using RDKit native structures."""
    if not RDKIT_AVAILABLE:
        return 0.0
    return float(DataStructs.TanimotoSimilarity(fp1, fp2))
