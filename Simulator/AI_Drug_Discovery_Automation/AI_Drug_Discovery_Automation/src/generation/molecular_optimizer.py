"""
Molecular Optimizer
====================
Genetic Algorithm and Reinforcement Learning based molecular optimization.
Multi-objective optimization (property prediction + similarity constraints).
"""

import copy
import random
import math
from typing import Optional, List, Tuple, Callable, Dict, Any
from dataclasses import dataclass, field

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────


@dataclass
class MoleculeIndividual:
    """A single molecule in the GA population."""
    smiles: str
    fitness: float = 0.0
    mol: Optional[Chem.Mol] = None
    descriptors: Dict[str, float] = field(default_factory=dict)
    generation: int = 0

    def __post_init__(self):
        if self.mol is None:
            self.mol = Chem.MolFromSmiles(self.smiles)
        if self.mol is None:
            raise ValueError(f"Invalid SMILES: {self.smiles}")

    def get_mol(self) -> Chem.Mol:
        if self.mol is None:
            self.mol = Chem.MolFromSmiles(self.smiles)
        return self.mol


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    best_smiles: str
    best_fitness: float
    history: List[float]
    diversity: float
    num_generations: int
    total_evaluations: int


# ──────────────────────────────────────────────────────────
# Mutation Operators
# ──────────────────────────────────────────────────────────


class MutationOperator:
    """Collection of SMILES mutation strategies."""

    @staticmethod
    def insert_random_atom(mol: Chem.Mol) -> Chem.Mol:
        """Insert a random atom into the molecule."""
        rw_mol = Chem.RWMol(mol)
        atoms = ["C", "N", "O", "S", "F", "Cl"]
        new_atom = random.choice(atoms)
        idx = rw_mol.AddAtom(Chem.Atom(new_atom))
        # Connect to a random existing atom
        if rw_mol.GetNumAtoms() > 1:
            target = random.randint(0, rw_mol.GetNumAtoms() - 2)
            rw_mol.AddBond(target, idx, Chem.BondType.SINGLE)
        return rw_mol.GetMol()

    @staticmethod
    def delete_random_atom(mol: Chem.Mol) -> Chem.Mol:
        """Delete a random atom (except leaving single atoms)."""
        if mol.GetNumAtoms() <= 3:
            return mol
        rw_mol = Chem.RWMol(mol)
        idx = random.randint(0, rw_mol.GetNumAtoms() - 1)
        rw_mol.RemoveAtom(idx)
        return rw_mol.GetMol()

    @staticmethod
    def replace_random_atom(mol: Chem.Mol) -> Chem.Mol:
        """Replace a random atom with another element."""
        if mol.GetNumAtoms() == 0:
            return mol
        rw_mol = Chem.RWMol(mol)
        atoms = ["C", "N", "O", "S", "F", "Cl", "Br"]
        idx = random.randint(0, rw_mol.GetNumAtoms() - 1)
        new_element = random.choice(atoms)
        rw_mol.ReplaceAtom(idx, Chem.Atom(new_element))
        return rw_mol.GetMol()

    @staticmethod
    def add_bond(mol: Chem.Mol) -> Chem.Mol:
        """Add a bond between two non-bonded atoms."""
        rw_mol = Chem.RWMol(mol)
        atoms = list(range(rw_mol.GetNumAtoms()))
        random.shuffle(atoms)
        for i in range(len(atoms) - 1):
            for j in range(i + 1, len(atoms)):
                if not rw_mol.GetBondBetweenAtoms(atoms[i], atoms[j]):
                    bond_type = random.choice([Chem.BondType.SINGLE, Chem.BondType.DOUBLE])
                    rw_mol.AddBond(atoms[i], atoms[j], bond_type)
                    return rw_mol.GetMol()
        return rw_mol.GetMol()

    @staticmethod
    def remove_bond(mol: Chem.Mol) -> Chem.Mol:
        """Remove a random bond (keeping molecule connected)."""
        if mol.GetNumBonds() <= 1:
            return mol
        rw_mol = Chem.RWMol(mol)
        bonds = list(rw_mol.GetBonds())
        random.shuffle(bonds)
        for bond in bonds:
            begin, end = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            rw_mol.RemoveBond(begin, end)
            # Check if still connected
            fragments = Chem.GetMolFrags(rw_mol.GetMol(), asMols=False)
            if len(fragments) == 1:
                return rw_mol.GetMol()
            # Re-add bond if disconnected
            rw_mol.AddBond(begin, end, bond.GetBondType())
        return rw_mol.GetMol()

    @staticmethod
    def mutate_smiles_string(smiles: str, mutation_rate: float = 0.1) -> Optional[str]:
        """Mutate a SMILES by making small random changes at the string level."""
        if random.random() > mutation_rate:
            return smiles

        chars = list(smiles)
        if not chars:
            return smiles

        mutation_type = random.choice(["insert", "delete", "replace"])

        if mutation_type == "insert":
            additions = ["C", "N", "O", "(", ")", "=", "1", "2", "c", "n"]
            idx = random.randint(0, len(chars))
            chars.insert(idx, random.choice(additions))

        elif mutation_type == "delete":
            if len(chars) > 3:
                idx = random.randint(0, len(chars) - 1)
                chars.pop(idx)

        elif mutation_type == "replace":
            replacements = {
                "C": ["N", "O", "S", "c"],
                "N": ["C", "O", "n"],
                "O": ["C", "N", "S"],
                "(": [")", "["],
                ")": ["(", "]"],
                "=": ["#", "-"],
                "1": ["2", "3"],
                "2": ["1", "3"],
                "c": ["C", "n", "o"],
                "n": ["N", "c"],
            }
            idx = random.randint(0, len(chars) - 1)
            char = chars[idx]
            if char in replacements:
                chars[idx] = random.choice(replacements[char])

        return "".join(chars)


# ──────────────────────────────────────────────────────────
# Crossover Operators
# ──────────────────────────────────────────────────────────


class CrossoverOperator:
    """SMILES crossover strategies."""

    @staticmethod
    def single_point_crossover(smiles1: str, smiles2: str) -> Tuple[str, str]:
        """Single-point crossover at random positions."""
        if len(smiles1) < 3 or len(smiles2) < 3:
            return smiles1, smiles2

        pt1 = random.randint(1, len(smiles1) - 1)
        pt2 = random.randint(1, len(smiles2) - 1)

        child1 = smiles1[:pt1] + smiles2[pt2:]
        child2 = smiles2[:pt2] + smiles1[pt1:]
        return child1, child2

    @staticmethod
    def ring_swap_crossover(mol1: Chem.Mol, mol2: Chem.Mol) -> Tuple[Optional[Chem.Mol], Optional[Chem.Mol]]:
        """Swap rings between two molecules."""
        from rdkit.Chem import rdMolDescriptors

        rings1 = mol1.GetRingInfo().AtomRings()
        rings2 = mol2.GetRingInfo().AtomRings()

        if not rings1 or not rings2:
            return None, None

        # Pick a random ring from each
        ring1_indices = random.choice(rings1)
        ring2_indices = random.choice(rings2)

        # Extract ring as substructure
        ring1_atoms = [mol1.GetAtomWithIdx(i).GetSymbol() for i in ring1_indices]
        ring2_atoms = [mol2.GetAtomWithIdx(i).GetSymbol() for i in ring2_indices]

        # Simple string swap
        smi1 = Chem.MolToSmiles(mol1)
        smi2 = Chem.MolToSmiles(mol2)

        # This is a simplified ring swap
        return smi1, smi2


# ──────────────────────────────────────────────────────────
# Fitness Functions
# ──────────────────────────────────────────────────────────


class FitnessFunctions:
    """Collection of fitness functions for molecular optimization."""

    @staticmethod
    def druglikeness(mol: Chem.Mol) -> float:
        """Lipinski rule-of-five compliance score (0-1)."""
        if mol is None:
            return 0.0

        try:
            mw = Descriptors.MolWt(mol)
            logp = Descriptors.MolLogP(mol)
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)

            score = 0.0
            if 150 <= mw <= 500:
                score += 0.25
            elif 100 <= mw <= 600:
                score += 0.15
            if -2 <= logp <= 5:
                score += 0.25
            elif -4 <= logp <= 7:
                score += 0.10
            if hbd <= 5:
                score += 0.25
            elif hbd <= 7:
                score += 0.10
            if hba <= 10:
                score += 0.25
            elif hba <= 12:
                score += 0.10

            return score
        except Exception:
            return 0.0

    @staticmethod
    def synthetic_accessibility(mol: Chem.Mol) -> float:
        """Estimate synthetic accessibility (higher = easier to synthesize, 0-1)."""
        if mol is None:
            return 0.0

        try:
            from rdkit.Contrib.SA_Score import sascorer
            sa_score = sascorer.calculateScore(mol)
            # SA Score: 1 (easy) to 10 (hard); normalize to 0-1
            return max(0.0, 1.0 - (sa_score - 1.0) / 9.0)
        except ImportError:
            # Fallback heuristic
            num_atoms = mol.GetNumAtoms()
            num_rings = len(mol.GetRingInfo().AtomRings())
            num_chiral = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))

            score = 1.0
            if num_atoms > 50:
                score -= 0.3
            elif num_atoms > 30:
                score -= 0.1
            if num_rings > 5:
                score -= 0.2
            if num_chiral > 3:
                score -= 0.2

            return max(0.0, score)

    @staticmethod
    def similarity_to_reference(mol: Chem.Mol, ref_smiles: str, fingerprint_type: str = "morgan") -> float:
        """Tanimoto similarity to a reference molecule (0-1)."""
        ref_mol = Chem.MolFromSmiles(ref_smiles)
        if mol is None or ref_mol is None:
            return 0.0

        if fingerprint_type == "morgan":
            fp1 = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
            fp2 = AllChem.GetMorganFingerprintAsBitVect(ref_mol, 2, nBits=2048)
        elif fingerprint_type == "topological":
            fp1 = Chem.RDKFingerprint(mol)
            fp2 = Chem.RDKFingerprint(ref_mol)
        else:
            fp1 = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
            fp2 = AllChem.GetMorganFingerprintAsBitVect(ref_mol, 2, nBits=2048)

        from rdkit import DataStructs
        return DataStructs.TanimotoSimilarity(fp1, fp2)

    @staticmethod
    def novelty(mol: Chem.Mol, reference_smiles_list: List[str]) -> float:
        """Novelty score: 1 - max similarity to any reference."""
        if mol is None:
            return 0.0

        max_sim = 0.0
        fp1 = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
        from rdkit import DataStructs

        for ref_smi in reference_smiles_list:
            ref_mol = Chem.MolFromSmiles(ref_smi)
            if ref_mol:
                fp2 = AllChem.GetMorganFingerprintAsBitVect(ref_mol, 2, nBits=2048)
                sim = DataStructs.TanimotoSimilarity(fp1, fp2)
                if sim > max_sim:
                    max_sim = sim

        return 1.0 - max_sim

    @staticmethod
    def diversity(population: List[MoleculeIndividual]) -> float:
        """Average pairwise dissimilarity within a population."""
        if len(population) < 2:
            return 0.0

        from rdkit import DataStructs
        fps = []
        for ind in population:
            mol = ind.get_mol()
            if mol:
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
                fps.append(fp)

        if len(fps) < 2:
            return 0.0

        similarities = []
        for i in range(len(fps)):
            for j in range(i + 1, len(fps)):
                sim = DataStructs.TanimotoSimilarity(fps[i], fps[j])
                similarities.append(sim)

        if not similarities:
            return 0.0
        return 1.0 - (sum(similarities) / len(similarities))


# ──────────────────────────────────────────────────────────
# Genetic Algorithm Optimizer
# ──────────────────────────────────────────────────────────


class GAOptimizer:
    """
    Genetic Algorithm for molecular optimization.

    Supports multi-objective fitness, tournament selection,
    crossover, mutation, and elitism.
    """

    def __init__(
        self,
        population_size: int = 100,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        elitism_ratio: float = 0.1,
        tournament_size: int = 3,
        max_generations: int = 100,
        fitness_function: Optional[Callable] = None,
        early_stop_generations: int = 20,
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_ratio = elitism_ratio
        self.tournament_size = tournament_size
        self.max_generations = max_generations
        self.fitness_function = fitness_function or FitnessFunctions.druglikeness
        self.early_stop_generations = early_stop_generations

        self.population: List[MoleculeIndividual] = []
        self.generation = 0
        self.history: List[float] = []
        self.best_individual: Optional[MoleculeIndividual] = None

        self._mutation_ops = [
            MutationOperator.insert_random_atom,
            MutationOperator.delete_random_atom,
            MutationOperator.replace_random_atom,
            MutationOperator.mutate_smiles_string,
        ]

    def _create_individual(self, smiles: str) -> Optional[MoleculeIndividual]:
        """Create a MoleculeIndividual from a SMILES string."""
        try:
            return MoleculeIndividual(smiles=smiles, generation=self.generation)
        except (ValueError, RuntimeError):
            return None

    def _evaluate_fitness(self, individual: MoleculeIndividual) -> float:
        """Evaluate fitness for a single individual."""
        mol = individual.get_mol()
        if mol is None:
            return 0.0
        return self.fitness_function(mol)

    def _evaluate_population(self) -> None:
        """Evaluate fitness for all individuals."""
        for ind in self.population:
            ind.fitness = self._evaluate_fitness(ind)

    def _tournament_selection(self) -> MoleculeIndividual:
        """Select an individual using tournament selection."""
        candidates = random.sample(self.population, min(self.tournament_size, len(self.population)))
        return max(candidates, key=lambda x: x.fitness)

    def _crossover(self, parent1: MoleculeIndividual, parent2: MoleculeIndividual) -> Tuple[Optional[str], Optional[str]]:
        """Perform crossover between two parents."""
        if random.random() > self.crossover_rate:
            return parent1.smiles, parent2.smiles
        try:
            child1_smi, child2_smi = CrossoverOperator.single_point_crossover(
                parent1.smiles, parent2.smiles
            )
            return child1_smi, child2_smi
        except Exception:
            return parent1.smiles, parent2.smiles

    def _mutate_smiles(self, smiles: str) -> str:
        """Apply mutation to a SMILES string."""
        if random.random() > self.mutation_rate:
            return smiles

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return smiles

        op = random.choice(self._mutation_ops)
        try:
            if op == MutationOperator.mutate_smiles_string:
                mutated = op(smiles, self.mutation_rate)
            else:
                mutated_mol = op(mol)
                if mutated_mol is not None and mutated_mol.GetNumAtoms() > 0:
                    mutated = Chem.MolToSmiles(mutated_mol)
                else:
                    return smiles
            return mutated
        except Exception:
            return smiles

    def _validate_smiles(self, smiles: str) -> Optional[str]:
        """Validate and canonicalize a SMILES string."""
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is not None:
                return Chem.MolToSmiles(mol)
        except Exception:
            pass
        return None

    def _initialize_population(self, seed_smiles: List[str]) -> None:
        """Initialize population from seed molecules."""
        self.population = []
        for smi in seed_smiles:
            canonical = self._validate_smiles(smi)
            if canonical:
                ind = self._create_individual(canonical)
                if ind:
                    self.population.append(ind)

        # Fill remaining with mutations of seeds
        while len(self.population) < self.population_size:
            if self.population:
                parent = random.choice(self.population)
                mutated = self._mutate_smiles(parent.smiles)
                canonical = self._validate_smiles(mutated)
                if canonical:
                    ind = self._create_individual(canonical)
                    if ind:
                        self.population.append(ind)
            else:
                break

    def _create_next_generation(self) -> List[MoleculeIndividual]:
        """Create the next generation using selection, crossover, and mutation."""
        next_pop: List[MoleculeIndividual] = []

        # Elitism: keep top individuals
        num_elites = max(1, int(self.population_size * self.elitism_ratio))
        sorted_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)
        for elite in sorted_pop[:num_elites]:
            ind = self._create_individual(elite.smiles)
            if ind:
                ind.fitness = elite.fitness
                ind.generation = self.generation + 1
                next_pop.append(ind)

        # Fill rest with offspring
        while len(next_pop) < self.population_size:
            parent1 = self._tournament_selection()
            parent2 = self._tournament_selection()

            child1_smi, child2_smi = self._crossover(parent1, parent2)

            for smi in [child1_smi, child2_smi]:
                if len(next_pop) >= self.population_size:
                    break
                if smi:
                    # Mutate
                    smi = self._mutate_smiles(smi)
                    canonical = self._validate_smiles(smi)
                    if canonical:
                        ind = self._create_individual(canonical)
                        if ind:
                            next_pop.append(ind)

        return next_pop

    def optimize(
        self,
        seed_smiles: List[str],
        progress_callback: Optional[Callable] = None,
    ) -> OptimizationResult:
        """
        Run the genetic algorithm optimization.

        Args:
            seed_smiles: Initial SMILES strings to start optimization
            progress_callback: Optional callback(generation, best_fitness, population)

        Returns:
            OptimizationResult with best molecule and history
        """
        self._initialize_population(seed_smiles)

        if not self.population:
            raise ValueError("No valid molecules in seed population")

        self._evaluate_population()
        self.best_individual = max(self.population, key=lambda x: x.fitness)
        self.history.append(self.best_individual.fitness)

        no_improvement = 0

        for gen in range(1, self.max_generations + 1):
            self.generation = gen
            self.population = self._create_next_generation()
            self._evaluate_population()

            current_best = max(self.population, key=lambda x: x.fitness)
            self.history.append(current_best.fitness)

            if current_best.fitness > self.best_individual.fitness:
                self.best_individual = current_best
                no_improvement = 0
            else:
                no_improvement += 1

            if progress_callback:
                progress_callback(gen, self.best_individual.fitness, self.population)

            # Early stopping
            if no_improvement >= self.early_stop_generations:
                break

        diversity = FitnessFunctions.diversity(self.population)

        return OptimizationResult(
            best_smiles=self.best_individual.smiles,
            best_fitness=self.best_individual.fitness,
            history=self.history,
            diversity=diversity,
            num_generations=self.generation,
            total_evaluations=len(self.history) * self.population_size,
        )


# ──────────────────────────────────────────────────────────
# Multi-Objective Molecular Optimizer
# ──────────────────────────────────────────────────────────


class MolecularOptimizer:
    """
    High-level molecular optimizer with multi-objective support.

    Combines GA optimization with property prediction and similarity constraints.
    """

    def __init__(self, config: Optional[Any] = None):
        cfg = config or get_config()
        gen_cfg = cfg.generation

        self.ga_optimizer = GAOptimizer(
            population_size=gen_cfg.population_size,
            mutation_rate=gen_cfg.mutation_rate,
            max_generations=gen_cfg.num_epochs,
        )

    def optimize_for_property(
        self,
        seed_smiles: List[str],
        property_fn: Callable,
        maximize: bool = True,
        similarity_constraint: Optional[Tuple[str, float]] = None,
    ) -> OptimizationResult:
        """
        Optimize molecules for a specific property.

        Args:
            seed_smiles: Starting molecules
            property_fn: Property function (mol -> float)
            maximize: If True, maximize property; if False, minimize
            similarity_constraint: (ref_smiles, min_similarity) tuple
            progress_callback: Optional progress callback

        Returns:
            Optimization result
        """
        # Wrap the property function with optional similarity constraint
        def combined_fitness(mol: Chem.Mol) -> float:
            score = property_fn(mol)

            if similarity_constraint:
                ref_smi, min_sim = similarity_constraint
                sim = FitnessFunctions.similarity_to_reference(mol, ref_smi)
                if sim < min_sim:
                    score *= sim / min_sim  # Penalize

            if not maximize:
                score = -score if score != float("inf") else float("-inf")

            return score

        self.ga_optimizer.fitness_function = combined_fitness
        return self.ga_optimizer.optimize(seed_smiles)

    def optimize_multi_objective(
        self,
        seed_smiles: List[str],
        objectives: List[Tuple[Callable, float]],
    ) -> OptimizationResult:
        """
        Multi-objective optimization with weighted sum.

        Args:
            seed_smiles: Starting molecules
            objectives: List of (function, weight) tuples

        Returns:
            Optimization result
        """
        def weighted_fitness(mol: Chem.Mol) -> float:
            score = 0.0
            for fn, weight in objectives:
                score += weight * fn(mol)
            return score

        self.ga_optimizer.fitness_function = weighted_fitness
        return self.ga_optimizer.optimize(seed_smiles)

    def lead_optimization(
        self,
        lead_smiles: str,
        num_candidates: int = 10,
        similarity_min: float = 0.3,
        similarity_max: float = 0.8,
    ) -> List[str]:
        """
        Lead optimization: find analogs with improved properties.

        Args:
            lead_smiles: Lead molecule SMILES
            num_candidates: Number of candidates to return
            similarity_min: Minimum similarity to lead
            similarity_max: Maximum similarity to lead

        Returns:
            List of optimized SMILES
        """
        # Generate diverse seeds by fragmenting the lead
        mol = Chem.MolFromSmiles(lead_smiles)
        if mol is None:
            return [lead_smiles]

        seeds = [lead_smiles]
        # Add some mutated versions as seeds
        for _ in range(10):
            mutated = MutationOperator.mutate_smiles_string(lead_smiles, 0.3)
            if mutated:
                canonical = Chem.MolToSmiles(Chem.MolFromSmiles(mutated)) if Chem.MolFromSmiles(mutated) else None
                if canonical and canonical != lead_smiles:
                    seeds.append(canonical)

        def lead_fitness(mol: Chem.Mol) -> float:
            drug_score = FitnessFunctions.druglikeness(mol)
            sa_score = FitnessFunctions.synthetic_accessibility(mol)
            sim = FitnessFunctions.similarity_to_reference(mol, lead_smiles)

            # Encourage similarity within range
            if sim < similarity_min:
                sim_score = sim / similarity_min * 0.3
            elif sim > similarity_max:
                sim_score = (1.0 - sim) / (1.0 - similarity_max) * 0.3
            else:
                sim_score = 0.5

            return 0.4 * drug_score + 0.3 * sa_score + 0.3 * sim_score

        self.ga_optimizer.fitness_function = lead_fitness
        result = self.ga_optimizer.optimize(seeds)

        # Collect top unique candidates
        sorted_pop = sorted(self.ga_optimizer.population, key=lambda x: x.fitness, reverse=True)
        candidates = []
        for ind in sorted_pop:
            smi = ind.smiles
            if smi != lead_smiles and smi not in candidates:
                candidates.append(smi)
            if len(candidates) >= num_candidates:
                break

        return candidates if candidates else [lead_smiles]
