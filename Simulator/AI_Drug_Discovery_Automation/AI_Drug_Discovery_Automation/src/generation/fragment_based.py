"""
Fragment-Based Drug Design (FBDD)
==================================
Fragment detection, linking, growing, and merging strategies
for de novo molecular design using RDKit.

References:
    - Bembenek et al. "De novo design of ligands by computational fragment growing"
    - Moriaud et al. "Fragment-based de novo design"
"""

from typing import Optional, List, Tuple, Dict, Set
from dataclasses import dataclass, field

import numpy as np
from rdkit import Chem
from rdkit.Chem import (
    AllChem, BRICS, Descriptors, Lipinski,
    rdMolDescriptors, rdFMCS, FragmentCatalog,
)
from rdkit.Chem.Scaffolds import MurckoScaffold

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────


@dataclass
class MolecularFragment:
    """A molecular fragment with attachment points."""
    smiles: str
    mol: Optional[Chem.Mol] = None
    weight: float = 0.0
    logp: float = 0.0
    num_hbd: int = 0
    num_hba: int = 0
    num_rotatable: int = 0
    attachment_points: List[int] = field(default_factory=list)
    fragment_type: str = "unknown"  # core, sidechain, linker, ring

    def __post_init__(self):
        if self.mol is None and self.smiles:
            self.mol = Chem.MolFromSmiles(self.smiles)
            if self.mol:
                self._compute_properties()

    def _compute_properties(self):
        """Compute molecular properties for the fragment."""
        if self.mol:
            try:
                self.weight = Descriptors.MolWt(self.mol)
                self.logp = Descriptors.MolLogP(self.mol)
                self.num_hbd = Descriptors.NumHDonors(self.mol)
                self.num_hba = Descriptors.NumHAcceptors(self.mol)
                self.num_rotatable = Descriptors.NumRotatableBonds(self.mol)
            except Exception:
                pass

    def is_valid(self, max_weight: float = 300.0) -> bool:
        """Check if fragment satisfies drug-like fragment rules (Rule of Three)."""
        if self.mol is None:
            return False
        return (
            self.weight <= max_weight
            and self.num_hbd <= 3
            and self.num_hba <= 3
            and self.num_rotatable <= 3
            and self.logp <= 3.0
        )


@dataclass
class FragmentLibrary:
    """Collection of molecular fragments."""
    fragments: List[MolecularFragment] = field(default_factory=list)
    name: str = "default"

    def add_fragment(self, fragment: MolecularFragment) -> None:
        self.fragments.append(fragment)

    def add_from_smiles(self, smiles_list: List[str]) -> int:
        """Add fragments from a list of SMILES strings."""
        count = 0
        for smi in smiles_list:
            frag = MolecularFragment(smiles=smi)
            if frag.mol is not None:
                self.fragments.append(frag)
                count += 1
        return count

    def filter_by_rule_of_three(self, max_weight: float = 300.0) -> "FragmentLibrary":
        """Filter fragments by Rule of Three."""
        filtered = [f for f in self.fragments if f.is_valid(max_weight)]
        return FragmentLibrary(fragments=filtered, name=f"{self.name}_filtered")

    def get_by_type(self, fragment_type: str) -> List[MolecularFragment]:
        """Get fragments of a specific type."""
        return [f for f in self.fragments if f.fragment_type == fragment_type]

    def __len__(self) -> int:
        return len(self.fragments)

    def __getitem__(self, idx: int) -> MolecularFragment:
        return self.fragments[idx]


# ──────────────────────────────────────────────────────────
# Fragment Detection
# ──────────────────────────────────────────────────────────


class FragmentDetector:
    """Detect and extract fragments from molecules."""

    @staticmethod
    def retrosynthetic_fragments(mol: Chem.Mol) -> List[MolecularFragment]:
        """Use BRICS decomposition for retrosynthetic fragmentation."""
        if mol is None:
            return []

        try:
            fragments = BRICS.BRICSDecompose(mol)
            result = []
            for smi in set(fragments):
                frag = MolecularFragment(smiles=smi, fragment_type="brics")
                if frag.mol is not None:
                    result.append(frag)
            return result
        except Exception:
            return []

    @staticmethod
    def murcko_scaffold(mol: Chem.Mol) -> Optional[MolecularFragment]:
        """Extract Murcko scaffold (core framework)."""
        if mol is None:
            return None
        try:
            scaffold = MurckoScaffold.GetScaffoldForMol(mol)
            if scaffold:
                smi = Chem.MolToSmiles(scaffold)
                return MolecularFragment(smiles=smi, fragment_type="core")
        except Exception:
            pass
        return None

    @staticmethod
    def ring_systems(mol: Chem.Mol) -> List[MolecularFragment]:
        """Extract individual ring systems."""
        if mol is None:
            return []

        ring_info = mol.GetRingInfo()
        if not ring_info.NumRings():
            return []

        try:
            # Get ring systems using RDKit's ring decomposition
            fragments = []
            ri = mol.GetRingInfo()
            atom_rings = ri.AtomRings()

            # Find connected ring systems
            if not atom_rings:
                return []

            # Simple approach: extract atoms belonging to rings
            ring_atoms = set()
            for ring in atom_rings:
                ring_atoms.update(ring)

            # Extract each disconnected ring system
            if ring_atoms:
                # Create a copy of mol with only ring atoms
                env = Chem.MolFromSmiles(Chem.MolFragmentToSmiles(mol, list(ring_atoms)))
                if env:
                    # Further decompose into separate ring systems
                    frags = Chem.GetMolFrags(env, asMols=True)
                    for f in frags:
                        smi = Chem.MolToSmiles(f)
                        if smi:
                            fragments.append(MolecularFragment(smiles=smi, fragment_type="ring"))
            return fragments
        except Exception:
            return []

    @staticmethod
    def functional_groups(mol: Chem.Mol) -> List[MolecularFragment]:
        """Detect common functional groups."""
        if mol is None:
            return []

        # Common functional group SMARTS patterns
        fg_patterns = {
            "carboxyl": "[CX3](=O)[OX2H1]",
            "hydroxyl": "[OX2H]",
            "amino": "[NX3;H2,H1;!$(NC=O)]",
            "amide": "[CX3](=O)[NX3]",
            "ester": "[CX3](=O)[OX2][CX4]",
            "ketone": "[CX3](=O)[CX3]",
            "aldehyde": "[CX3H1](=O)[#6]",
            "ether": "[OD2]([#6])[#6]",
            "nitro": "[NX3](=O)=O",
            "sulfonyl": "[SX4](=O)(=O)[#6]",
            "halogen": "[F,Cl,Br,I]",
            "cyano": "[NX1]#[CX2]",
            "phenyl": "c1ccccc1",
            "pyridine": "c1ncccc1",
        }

        fragments = []
        for name, smarts in fg_patterns.items():
            try:
                pat = Chem.MolFromSmarts(smarts)
                if pat and mol.HasSubstructMatch(pat):
                    matches = mol.GetSubstructMatches(pat)
                    for match in matches:
                        if match:
                            env = Chem.MolFromSmiles(
                                Chem.MolFragmentToSmiles(mol, list(match))
                            )
                            if env:
                                smi = Chem.MolToSmiles(env)
                                if smi:
                                    frag = MolecularFragment(
                                        smiles=smi, fragment_type=f"fg_{name}"
                                    )
                                    if frag.mol and smi not in [f.smiles for f in fragments]:
                                        fragments.append(frag)
            except Exception:
                continue

        return fragments


# ──────────────────────────────────────────────────────────
# Fragment Linking and Growing
# ──────────────────────────────────────────────────────────


class FragmentLinker:
    """
    Link fragments together to form larger molecules.
    Supports various linking strategies.
    """

    # Common linker atoms/groups
    LINKERS = [
        "",       # direct bond
        "C",      # methylene
        "CC",     # ethylene
        "C=C",    # ethene
        "C#C",    # ethyne
        "O",      # ether
        "S",      # thioether
        "NH",     # amine
        "C(=O)",  # carbonyl
        "C(=O)NH",  # amide
        "C(=O)O",   # ester
        "N=N",    # azo
        "c1ccccc1",  # phenyl
    ]

    @staticmethod
    def link_fragments(frag1: MolecularFragment, frag2: MolecularFragment,
                       linker: str = "C") -> Optional[str]:
        """
        Link two fragments with a linker.

        Args:
            frag1: First fragment
            frag2: Second fragment
            linker: Linker SMILES (default: methylene)

        Returns:
            Linked molecule SMILES or None if invalid
        """
        try:
            if "." in linker:
                # Multiple components: link sequentially
                return None

            if not linker:
                # Direct bond
                combined = f"{frag1.smiles}{frag2.smiles}"
            else:
                combined = f"{frag1.smiles}{linker}{frag2.smiles}"

            mol = Chem.MolFromSmiles(combined)
            if mol:
                return Chem.MolToSmiles(mol)
        except Exception:
            pass
        return None

    @staticmethod
    def grow_fragment(fragment: MolecularFragment, growth_smiles: str,
                      attachment_point: Optional[int] = None) -> Optional[str]:
        """
        Grow a fragment by adding a functional group.

        Args:
            fragment: Base fragment
            growth_smiles: SMILES of group to add
            attachment_point: Optional atom index to attach to

        Returns:
            Grown molecule SMILES or None
        """
        try:
            combined = f"{fragment.smiles}{growth_smiles}"
            mol = Chem.MolFromSmiles(combined)
            if mol:
                return Chem.MolToSmiles(mol)
        except Exception:
            pass
        return None

    @staticmethod
    def merge_fragments(frag1: MolecularFragment, frag2: MolecularFragment) -> Optional[str]:
        """
        Merge two fragments by finding a common substructure.

        Uses Maximum Common Substructure (MCS) alignment.
        """
        try:
            mcs = rdFMCS.FindMCS([frag1.mol, frag2.mol])
            if mcs.numAtoms == 0:
                return None

            mcs_mol = Chem.MolFromSmarts(mcs.smartsString)
            if mcs_mol is None:
                return None

            # Align and merge (simplified: just combine)
            combined = Chem.CombineMols(frag1.mol, frag2.mol)
            return Chem.MolToSmiles(combined)
        except Exception:
            return None

    @staticmethod
    def scaffold_hop(fragment: MolecularFragment, target_scaffold_smiles: str) -> Optional[str]:
        """
        Replace fragment core with a different scaffold.

        Args:
            fragment: Original fragment
            target_scaffold_smiles: New scaffold SMILES

        Returns:
            New molecule SMILES
        """
        try:
            new_mol = Chem.MolFromSmiles(target_scaffold_smiles)
            if new_mol is None:
                return None
            return Chem.MolToSmiles(new_mol)
        except Exception:
            return None


# ──────────────────────────────────────────────────────────
# Fragment-Based Design
# ──────────────────────────────────────────────────────────


class FragmentBasedDesign:
    """
    Fragment-based drug design orchestrator.

    Strategies:
        - Fragment linking: link two fragments with a suitable linker
        - Fragment growing: grow fragment by adding functional groups
        - Fragment merging: merge overlapping fragments
        - Scaffold hopping: replace core scaffold
    """

    def __init__(self, fragment_library: Optional[FragmentLibrary] = None):
        self.fragment_library = fragment_library or FragmentLibrary()
        self.detector = FragmentDetector()
        self.linker = FragmentLinker()

    def decompose_molecule(self, smiles: str) -> Dict[str, List[MolecularFragment]]:
        """
        Fully decompose a molecule into fragments.

        Returns:
            Dictionary with fragment types as keys
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {}

        result = {
            "scaffold": [],
            "rings": [],
            "brics": [],
            "functional_groups": [],
        }

        scaffold = self.detector.murcko_scaffold(mol)
        if scaffold:
            result["scaffold"] = [scaffold]

        result["rings"] = self.detector.ring_systems(mol)
        result["brics"] = self.detector.retrosynthetic_fragments(mol)
        result["functional_groups"] = self.detector.functional_groups(mol)

        return result

    def build_from_fragments(
        self,
        core_fragment: MolecularFragment,
        side_chains: List[MolecularFragment],
        linker: str = "C",
    ) -> List[str]:
        """
        Build new molecules by attaching side chains to a core.

        Args:
            core_fragment: Core scaffold fragment
            side_chains: List of side chain fragments
            linker: Linker SMILES

        Returns:
            List of resulting molecule SMILES
        """
        results = []
        for sc in side_chains:
            combined = self.linker.link_fragments(core_fragment, sc, linker)
            if combined:
                results.append(combined)
        return results

    def generate_library(
        self,
        core_smiles: List[str],
        side_chain_smiles: List[str],
        linkers: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Generate a virtual library by combining cores with side chains.

        Args:
            core_smiles: List of core scaffold SMILES
            side_chain_smiles: List of side chain SMILES
            linkers: List of linkers to try (default: all common linkers)

        Returns:
            List of generated molecule SMILES
        """
        if linkers is None:
            linkers = FragmentLinker.LINKERS[:5]  # First 5 linkers

        library = set()
        for core_smi in core_smiles:
            core_frag = MolecularFragment(smiles=core_smi, fragment_type="core")
            if core_frag.mol is None:
                continue

            for sc_smi in side_chain_smiles:
                sc_frag = MolecularFragment(smiles=sc_smi, fragment_type="sidechain")
                if sc_frag.mol is None:
                    continue

                for linker in linkers:
                    result = self.linker.link_fragments(core_frag, sc_frag, linker)
                    if result:
                        library.add(result)

        return list(library)

    def design_by_growing(
        self,
        seed_fragment_smiles: str,
        growth_blocks: List[str],
        max_growth_steps: int = 3,
    ) -> List[str]:
        """
        Iteratively grow a fragment by adding growth blocks.

        Args:
            seed_fragment_smiles: Starting fragment
            growth_blocks: List of SMILES to add at each step
            max_growth_steps: Maximum number of growth steps

        Returns:
            List of grown molecule SMILES
        """
        current = seed_fragment_smiles
        results = {current}

        for step in range(max_growth_steps):
            next_generation = set()
            for smi in results:
                frag = MolecularFragment(smiles=smi)
                if frag.mol is None:
                    continue

                for gb in growth_blocks:
                    grown = self.linker.grow_fragment(frag, gb)
                    if grown:
                        next_generation.add(grown)

            results.update(next_generation)

        return list(results)

    def diversity_analysis(self, smiles_list: List[str]) -> Dict[str, float]:
        """
        Analyze diversity of a set of molecules.

        Returns:
            Dictionary with diversity metrics
        """
        if len(smiles_list) < 2:
            return {"diversity": 0.0, "num_molecules": len(smiles_list)}

        from rdkit import DataStructs

        mols = []
        fps = []
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol:
                mols.append(mol)
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
                fps.append(fp)

        if len(fps) < 2:
            return {"diversity": 0.0, "num_molecules": len(fps)}

        # Average pairwise similarity
        similarities = []
        for i in range(len(fps)):
            for j in range(i + 1, len(fps)):
                sim = DataStructs.TanimotoSimilarity(fps[i], fps[j])
                similarities.append(sim)

        avg_similarity = np.mean(similarities) if similarities else 0.0

        # Number of unique scaffolds
        scaffolds = set()
        for mol in mols:
            try:
                scaffold = MurckoScaffold.GetScaffoldForMol(mol)
                if scaffold:
                    scaffolds.add(Chem.MolToSmiles(scaffold))
            except Exception:
                pass

        return {
            "diversity": 1.0 - avg_similarity,
            "avg_similarity": avg_similarity,
            "num_molecules": len(mols),
            "num_unique_scaffolds": len(scaffolds),
            "scaffold_diversity": len(scaffolds) / max(1, len(mols)),
        }

    def load_fragment_library_from_file(self, filepath: str) -> int:
        """
        Load fragments from a SMILES file.

        Args:
            filepath: Path to file with one SMILES per line

        Returns:
            Number of fragments loaded
        """
        try:
            with open(filepath) as f:
                smiles_list = [line.strip() for line in f if line.strip()]
            return self.fragment_library.add_from_smiles(smiles_list)
        except Exception:
            return 0

    def analyze_fragment_library(self) -> Dict[str, Any]:
        """Analyze the fragment library composition."""
        if not self.fragment_library.fragments:
            return {"count": 0}

        weights = [f.weight for f in self.fragment_library.fragments if f.mol]
        logps = [f.logp for f in self.fragment_library.fragments if f.mol]

        return {
            "count": len(self.fragment_library),
            "avg_weight": np.mean(weights) if weights else 0,
            "avg_logp": np.mean(logps) if logps else 0,
            "rule_of_three_pass": sum(1 for f in self.fragment_library.fragments if f.is_valid()),
            "types": {
                "core": len(self.fragment_library.get_by_type("core")),
                "ring": len(self.fragment_library.get_by_type("ring")),
                "sidechain": len(self.fragment_library.get_by_type("sidechain")),
                "brics": len(self.fragment_library.get_by_type("brics")),
            },
        }
