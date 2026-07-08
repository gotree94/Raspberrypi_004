"""
Docking Scoring and Analysis
==============================
Binding affinity scoring, consensus scoring, and result analysis.

Supports:
    - Vina scoring function integration
    - Consensus scoring across multiple methods
    - Binding mode analysis (RMSD clustering)
    - Interaction fingerprint analysis
"""

from typing import Optional, List, Dict, Tuple, Any, Callable
from dataclasses import dataclass, field
from collections import Counter

import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem, rdMolDescriptors

from src.docking.autodock_vina import DockingResult, DockingPose


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────


@dataclass
class InteractionProfile:
    """Protein-ligand interaction profile."""
    hydrogen_bonds: List[Dict] = field(default_factory=list)
    hydrophobic: List[Dict] = field(default_factory=list)
    pi_stacking: List[Dict] = field(default_factory=list)
    ionic_interactions: List[Dict] = field(default_factory=list)
    halogen_bonds: List[Dict] = field(default_factory=list)
    salt_bridges: List[Dict] = field(default_factory=list)

    @property
    def total_interactions(self) -> int:
        return sum(len(v) for v in self.__dict__.values())


@dataclass
class ScoreResult:
    """Individual scoring function result."""
    score: float
    weight: float = 1.0
    name: str = ""


# ──────────────────────────────────────────────────────────
# Scoring Functions
# ──────────────────────────────────────────────────────────


class ScoringFunction:
    """
    Collection of scoring functions for binding affinity estimation.

    Includes:
        - Vina score (via subprocess)
        - Drug-likeness score
        - Shape complementarity score
        - Electrostatic score
    """

    @staticmethod
    def vina_score(receptor_pdbqt: str, ligand_pdbqt: str) -> float:
        """
        Run Vina score-only mode.

        Args:
            receptor_pdbqt: Path to receptor PDBQT
            ligand_pdbqt: Path to ligand PDBQT

        Returns:
            Binding affinity (kcal/mol, lower = better)
        """
        from src.docking.autodock_vina import VinaDocker, BindingBox
        docker = VinaDocker()
        return docker.score(receptor_pdbqt, ligand_pdbqt)

    @staticmethod
    def druglikeness_score(smiles: str) -> float:
        """
        Drug-likeness score based on Lipinski and Veber rules.

        Returns:
            Score from 0 (poor) to 1 (excellent)
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return 0.0

        from rdkit.Chem import Descriptors, Lipinski

        score = 0.0
        # Lipinski
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = Descriptors.NumHDonors(mol)
        hba = Descriptors.NumHAcceptors(mol)

        lipinski_score = sum([
            150 <= mw <= 500,
            -2 <= logp <= 5,
            hbd <= 5,
            hba <= 10,
        ]) / 4.0

        # Veber
        rb = Descriptors.NumRotatableBonds(mol)
        tpsa = Descriptors.TPSA(mol)
        veber_score = sum([
            rb <= 10,
            tpsa <= 140,
            rb > 0,
        ]) / 3.0

        score = 0.6 * lipinski_score + 0.4 * veber_score
        return score

    @staticmethod
    def synthetic_accessibility(smiles: str) -> float:
        """
        Synthetic accessibility score (1=easy, 10=hard).

        Returns:
            SA score (lower = easier to synthesize)
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return 10.0

        try:
            from rdkit.Contrib.SA_Score import sascorer
            return sascorer.calculateScore(mol)
        except ImportError:
            # Heuristic fallback
            if mol:
                num_atoms = mol.GetNumAtoms()
                num_rings = len(mol.GetRingInfo().AtomRings())
                num_chiral = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))

                score = 1.0
                if num_atoms > 50:
                    score += 4.0
                elif num_atoms > 30:
                    score += 2.0
                if num_rings > 5:
                    score += 2.0
                if num_chiral > 3:
                    score += 2.0
                return min(10.0, score)
            return 5.0

    @staticmethod
    def ligand_efficiency(binding_affinity: float, smiles: str) -> float:
        """
        Ligand Efficiency: binding affinity per heavy atom.

        LE = -ΔG / N_heavy_atoms

        Args:
            binding_affinity: Binding affinity (kcal/mol, negative value)
            smiles: Ligand SMILES

        Returns:
            Ligand efficiency (higher = better)
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None or binding_affinity >= 0:
            return 0.0

        num_heavy = mol.GetNumHeavyAtoms()
        if num_heavy == 0:
            return 0.0

        return -binding_affinity / num_heavy

    @staticmethod
    def lipophilic_efficiency(binding_affinity: float, smiles: str) -> float:
        """
        Lipophilic Efficiency: binding affinity per logP unit.

        LiPE = -ΔG / logP

        Args:
            binding_affinity: Binding affinity (kcal/mol)
            smiles: Ligand SMILES

        Returns:
            Lipophilic efficiency (higher = better)
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None or binding_affinity >= 0:
            return 0.0

        from rdkit.Chem import Descriptors
        logp = Descriptors.MolLogP(mol)
        if logp <= 0:
            return 0.0

        return -binding_affinity / logp


# ──────────────────────────────────────────────────────────
# Consensus Scorer
# ──────────────────────────────────────────────────────────


class ConsensusScorer:
    """
    Consensus scoring across multiple scoring methods.

    Combines multiple scores with weights to produce a
    consensus ranking of docking results.
    """

    def __init__(self):
        self.scorers: List[Tuple[str, Callable, float]] = []

    def add_scorer(self, name: str, scorer_fn: Callable, weight: float = 1.0) -> None:
        """
        Add a scoring function to the consensus.

        Args:
            name: Scorer name
            scorer_fn: Function that takes (DockingResult) → float
            weight: Weight in consensus (higher = more important)
        """
        self.scorers.append((name, scorer_fn, weight))

    def score(self, result: DockingResult) -> Dict[str, float]:
        """
        Compute consensus score for a docking result.

        Returns:
            Dictionary with individual scores and 'consensus' key
        """
        scores = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for name, fn, weight in self.scorers:
            try:
                score = fn(result)
                scores[name] = score
                weighted_sum += score * weight
                total_weight += weight
            except Exception:
                scores[name] = 0.0

        scores["consensus"] = weighted_sum / total_weight if total_weight > 0 else 0.0
        return scores

    def rank_results(self, results: List[DockingResult]) -> List[Tuple[DockingResult, float]]:
        """
        Rank docking results by consensus score.

        Args:
            results: List of docking results to rank

        Returns:
            List of (result, consensus_score) sorted by score (descending)
        """
        scored = []
        for result in results:
            if result.status == "success":
                scores = self.score(result)
                scored.append((result, scores["consensus"]))
            else:
                scored.append((result, float("-inf")))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# ──────────────────────────────────────────────────────────
# Score Analysis
# ──────────────────────────────────────────────────────────


class ScoreAnalyzer:
    """
    Analyze and compare docking scores across multiple ligands and methods.
    """

    @staticmethod
    def compare_results(results: List[DockingResult]) -> Dict:
        """
        Compare and rank multiple docking results.

        Args:
            results: List of docking results

        Returns:
            Dictionary with ranking and statistics
        """
        successful = [r for r in results if r.status == "success"]

        if not successful:
            return {"ranking": [], "statistics": {}}

        # Sort by best affinity (lower = better)
        ranked = sorted(successful, key=lambda r: r.best_affinity)

        # Compute statistics
        affinities = [r.best_affinity for r in successful]

        return {
            "ranking": [
                {
                    "rank": i + 1,
                    "ligand": r.ligand_name,
                    "smiles": r.ligand_smiles,
                    "best_affinity": r.best_affinity,
                    "num_poses": r.num_poses,
                }
                for i, r in enumerate(ranked)
            ],
            "statistics": {
                "best": min(affinities) if affinities else 0,
                "worst": max(affinities) if affinities else 0,
                "mean": float(np.mean(affinities)) if affinities else 0,
                "median": float(np.median(affinities)) if affinities else 0,
                "std": float(np.std(affinities)) if affinities else 0,
                "count": len(successful),
                "total": len(results),
            },
        }

    @staticmethod
    def cluster_poses(poses: List[DockingPose], rmsd_cutoff: float = 2.0) -> Dict[int, List[int]]:
        """
        Cluster docking poses by RMSD.

        Args:
            poses: List of docking poses
            rmsd_cutoff: RMSD cutoff for clustering (Angstroms)

        Returns:
            Dict mapping cluster ID to list of pose modes
        """
        if not poses:
            return {}

        # Simple greedy clustering using reported RMSD
        clusters: Dict[int, List[int]] = {}
        assigned = set()

        for i, pose in enumerate(poses):
            if pose.mode in assigned:
                continue

            cluster_id = i + 1
            clusters[cluster_id] = [pose.mode]
            assigned.add(pose.mode)

            for j, other in enumerate(poses):
                if other.mode in assigned:
                    continue
                if other.rmsd_lower <= rmsd_cutoff:
                    clusters[cluster_id].append(other.mode)
                    assigned.add(other.mode)

        return clusters

    @staticmethod
    def enrichment_factor(results: List[DockingResult], top_fraction: float = 0.05, threshold: float = -9.0) -> float:
        """
        Calculate enrichment factor at given fraction.

        EF = (Hits_selected / N_selected) / (Hits_total / N_total)

        Args:
            results: List of docking results
            top_fraction: Fraction of top-ranked compounds to consider
            threshold: Affinity threshold for "hit" (kcal/mol, more negative = better)

        Returns:
            Enrichment factor
        """
        successful = [r for r in results if r.status == "success"]
        if not successful:
            return 0.0

        # Sort by affinity
        sorted_results = sorted(successful, key=lambda r: r.best_affinity)
        n_total = len(sorted_results)
        n_select = max(1, int(n_total * top_fraction))

        hits_total = sum(1 for r in sorted_results if r.best_affinity <= threshold)
        hits_selected = sum(1 for r in sorted_results[:n_select] if r.best_affinity <= threshold)

        if hits_total == 0:
            return 0.0

        ef = (hits_selected / n_select) / (hits_total / n_total)
        return ef

    @staticmethod
    def summarize_hits(
        results: List[DockingResult],
        affinity_cutoff: float = -8.0,
    ) -> List[Dict]:
        """
        Identify and summarize high-affinity hits.

        Args:
            results: List of docking results
            affinity_cutoff: Affinity cutoff for "hit" (kcal/mol)

        Returns:
            List of hit summaries
        """
        hits = []
        for r in results:
            if r.status == "success" and r.best_affinity <= affinity_cutoff:
                hits.append({
                    "ligand_name": r.ligand_name,
                    "smiles": r.ligand_smiles,
                    "best_affinity": r.best_affinity,
                    "num_poses": r.num_poses,
                    "affinity_range": list(r.affinity_range),
                    "consistency": 1.0 - (r.affinity_range[1] - r.affinity_range[0]) / abs(r.best_affinity)
                    if r.best_affinity != 0 else 0.0,
                })

        hits.sort(key=lambda h: h["best_affinity"])
        return hits

    @staticmethod
    def to_dataframe(results: List[DockingResult]) -> Any:
        """
        Convert results to a pandas DataFrame.

        Args:
            results: List of docking results

        Returns:
            pandas DataFrame or None if pandas unavailable
        """
        try:
            import pandas as pd
            data = []
            for r in results:
                data.append({
                    "ligand": r.ligand_name,
                    "smiles": r.ligand_smiles,
                    "best_affinity": r.best_affinity,
                    "num_poses": r.num_poses,
                    "mean_affinity": r.mean_affinity,
                    "status": r.status,
                    "runtime": r.runtime_seconds,
                })
                # Add individual poses
                for pose in r.poses:
                    data.append({
                        "ligand": r.ligand_name,
                        "smiles": r.ligand_smiles,
                        f"pose_{pose.mode}": pose.affinity,
                    })

            return pd.DataFrame(data)
        except ImportError:
            return None
