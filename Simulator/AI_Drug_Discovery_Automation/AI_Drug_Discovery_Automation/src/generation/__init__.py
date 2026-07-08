"""
Molecular Generation Module
============================
VAE 기반 de novo 분자 생성, 유전 알고리즘 최적화, 단편 기반 설계.

Modules:
    vae_model          : PyTorch VAE for SMILES generation
    molecular_optimizer: Genetic Algorithm & RL-based optimization
    fragment_based     : Fragment-based drug design (FBDD)
"""
from src.generation.vae_model import SMILESVAE, VAETrainer
from src.generation.molecular_optimizer import MolecularOptimizer, GAOptimizer
from src.generation.fragment_based import FragmentBasedDesign, FragmentLinker

__all__ = [
    "SMILESVAE", "VAETrainer",
    "MolecularOptimizer", "GAOptimizer",
    "FragmentBasedDesign", "FragmentLinker",
]
