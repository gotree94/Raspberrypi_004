"""
Similarity Search Module
========================

Ligand-based virtual screening using molecular fingerprint similarity.
"""

import json
import pickle
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

from src.molecular.fingerprint import (
    MorganFingerprintGenerator,
    MACCSFingerprintGenerator,
    tanimoto_similarity,
    nearest_neighbors,
    compute_similarity_matrix,
)


# ──────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────


@dataclass
class CompoundLibrary:
    """A compound entry in the screening library."""
    id: str
    smiles: str
    name: str = ""
    properties: Dict[str, float] = field(default_factory=dict)
    fingerprint: Optional[np.ndarray] = None
    source: str = ""


@dataclass
class HitResult:
    """A screening hit result."""
    compound_id: str
    smiles: str
    similarity_score: float = 0.0
    properties: Dict[str, float] = field(default_factory=dict)
    rank: int = 0
    method: str = "similarity"

    def to_dict(self) -> Dict:
        return {
            "compound_id": self.compound_id,
            "smiles": self.smiles,
            "similarity_score": round(self.similarity_score, 4),
            "properties": self.properties,
            "rank": self.rank,
            "method": self.method,
        }


# ──────────────────────────────────────────────────────────
# Similarity Searcher
# ──────────────────────────────────────────────────────────


class SimilaritySearcher:
    """
    Ligand-based virtual screening via fingerprint similarity.

    Usage:
        searcher = SimilaritySearcher(fingerprint_type='morgan')
        searcher.build_index(compounds)
        hits = searcher.search("CC(=O)Oc1ccccc1C(=O)O", n_hits=100)
    """

    def __init__(
        self,
        fingerprint_type: str = "morgan",
        similarity_metric: str = "tanimoto",
        radius: int = 2,
        nbits: int = 2048,
    ):
        """
        Initialize the similarity searcher.

        Args:
            fingerprint_type: 'morgan', 'maccs', 'topological', 'rdkit'
            similarity_metric: 'tanimoto', 'dice', 'cosine'
            radius: Morgan fingerprint radius.
            nbits: Fingerprint bit length.
        """
        self.fingerprint_type = fingerprint_type
        self.similarity_metric = similarity_metric
        self.radius = radius
        self.nbits = nbits

        # Initialize fingerprint generator
        if fingerprint_type == "morgan":
            self.fp_gen = MorganFingerprintGenerator(radius=radius, nbits=nbits)
        elif fingerprint_type == "maccs":
            self.fp_gen = MACCSFingerprintGenerator()
        else:
            self.fp_gen = MorganFingerprintGenerator(radius=radius, nbits=nbits)

        # Library storage
        self.compounds: List[CompoundLibrary] = []
        self.fingerprints: List[np.ndarray] = []
        self.is_indexed = False

    def build_index(self, compounds: List[CompoundLibrary]) -> None:
        """
        Build the similarity search index from a list of compounds.

        Args:
            compounds: List of CompoundLibrary objects with SMILES.
        """
        if not RDKIT_AVAILABLE:
            logger.error("RDKit is required for fingerprint computation.")
            return

        self.compounds = list(compounds)
        self.fingerprints = []

        for i, cpd in enumerate(self.compounds):
            mol = Chem.MolFromSmiles(cpd.smiles)
            if mol is None:
                logger.warning(f"Invalid SMILES at index {i}: {cpd.smiles[:50]}")
                self.fingerprints.append(np.zeros(self.nbits))
            else:
                fp = self.fp_gen.generate(mol)
                self.fingerprints.append(fp)
                self.compounds[i].fingerprint = fp

        self.is_indexed = True
        n_valid = sum(1 for fp in self.fingerprints if np.any(fp))
        logger.info(f"Index built: {len(compounds)} compounds ({n_valid} with valid fingerprints)")

    def search(
        self,
        query: str,
        n_hits: int = 100,
        threshold: float = 0.0,
    ) -> List[HitResult]:
        """
        Search for compounds similar to the query.

        Args:
            query: SMILES string of the query compound.
            n_hits: Maximum number of hits to return.
            threshold: Minimum similarity threshold.

        Returns:
            List of HitResult objects, sorted by similarity descending.
        """
        if not self.is_indexed:
            raise ValueError("No index built. Call build_index() first.")

        if not RDKIT_AVAILABLE:
            return []

        mol = Chem.MolFromSmiles(query)
        if mol is None:
            raise ValueError(f"Invalid query SMILES: {query}")

        query_fp = self.fp_gen.generate(mol)

        neighbors = nearest_neighbors(
            query_fp, self.fingerprints, k=n_hits, threshold=threshold
        )

        hits = []
        for idx, score in neighbors:
            cpd = self.compounds[idx]
            hits.append(HitResult(
                compound_id=cpd.id,
                smiles=cpd.smiles,
                similarity_score=score,
                properties=cpd.properties,
                rank=len(hits) + 1,
                method=f"{self.fingerprint_type}_{self.similarity_metric}",
            ))

        logger.info(f"Similarity search: {len(hits)} hits (threshold={threshold})")
        return hits

    def search_by_fingerprint(
        self,
        query_fp: np.ndarray,
        n_hits: int = 100,
        threshold: float = 0.0,
    ) -> List[HitResult]:
        """
        Search using a pre-computed fingerprint.

        Args:
            query_fp: Query fingerprint vector.
            n_hits: Maximum number of hits.
            threshold: Minimum similarity threshold.

        Returns:
            List of HitResult objects.
        """
        if not self.is_indexed:
            raise ValueError("No index built.")

        neighbors = nearest_neighbors(
            query_fp, self.fingerprints, k=n_hits, threshold=threshold
        )

        hits = []
        for idx, score in neighbors:
            cpd = self.compounds[idx]
            hits.append(HitResult(
                compound_id=cpd.id,
                smiles=cpd.smiles,
                similarity_score=score,
                properties=cpd.properties,
                rank=len(hits) + 1,
            ))

        return hits

    def batch_search(
        self,
        queries: List[str],
        n_hits: int = 50,
        threshold: float = 0.5,
    ) -> List[List[HitResult]]:
        """
        Search multiple queries against the index.

        Args:
            queries: List of SMILES strings.
            n_hits: Maximum hits per query.
            threshold: Similarity threshold.

        Returns:
            List of hit lists (one per query).
        """
        results = []
        for q in queries:
            hits = self.search(q, n_hits=n_hits, threshold=threshold)
            results.append(hits)
        return results

    def add_compounds(self, compounds: List[CompoundLibrary]) -> None:
        """Add new compounds to the existing index."""
        self.build_index(self.compounds + compounds)

    def remove_compound(self, cpd_id: str) -> bool:
        """Remove a compound from the index by ID."""
        for i, cpd in enumerate(self.compounds):
            if cpd.id == cpd_id:
                self.compounds.pop(i)
                self.fingerprints.pop(i)
                logger.info(f"Removed compound {cpd_id}")
                return True
        return False

    def get_compound(self, cpd_id: str) -> Optional[CompoundLibrary]:
        """Get a compound by ID."""
        for cpd in self.compounds:
            if cpd.id == cpd_id:
                return cpd
        return None

    def statistics(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self.is_indexed:
            return {"indexed": False, "count": 0}
        return {
            "indexed": True,
            "count": len(self.compounds),
            "fingerprint_type": self.fingerprint_type,
            "fingerprint_bits": self.nbits,
            "similarity_metric": self.similarity_metric,
        }

    def save_index(self, path: str) -> None:
        """Save the index to disk."""
        data = {
            "fingerprint_type": self.fingerprint_type,
            "nbits": self.nbits,
            "compounds": [
                {
                    "id": c.id,
                    "smiles": c.smiles,
                    "name": c.name,
                    "properties": c.properties,
                    "source": c.source,
                }
                for c in self.compounds
            ],
            "fingerprints": [fp.tolist() for fp in self.fingerprints],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"Index saved to {path} ({len(self.compounds)} compounds)")

    def load_index(self, path: str) -> None:
        """Load a saved index from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.fingerprint_type = data["fingerprint_type"]
        self.nbits = data["nbits"]
        self.compounds = [
            CompoundLibrary(**c) for c in data["compounds"]
        ]
        self.fingerprints = [np.array(fp, dtype=np.float32) for fp in data["fingerprints"]]
        self.is_indexed = True

        # Re-init fingerprint generator
        if self.fingerprint_type == "morgan":
            self.fp_gen = MorganFingerprintGenerator(radius=self.radius, nbits=self.nbits)
        elif self.fingerprint_type == "maccs":
            self.fp_gen = MACCSFingerprintGenerator()

        logger.info(f"Index loaded from {path} ({len(self.compounds)} compounds)")

    def __len__(self) -> int:
        return len(self.compounds)

    def __repr__(self) -> str:
        return (f"SimilaritySearcher(type={self.fingerprint_type}, "
                f"compounds={len(self.compounds)}, indexed={self.is_indexed})")
