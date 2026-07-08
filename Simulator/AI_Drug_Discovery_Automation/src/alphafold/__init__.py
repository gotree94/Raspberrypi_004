"""
AlphaFold Integration Module
============================

AlphaFold2/3 단백질 구조 예측 통합 모듈.

실제 AlphaFold2/3 바이너리, Docker 컨테이너, 또는 Google Colab을 통해
단백질 아미노산 서열로부터 3차원 구조를 예측합니다.

Supports:
    - AlphaFold2 (Local / Docker / Colab)
    - AlphaFold3 (Local / Docker)
    - Multimer prediction
    - Batch sequence processing
    - Confidence metrics extraction (pLDDT, PAE)
"""

from src.alphafold.alphafold_wrapper import AlphaFoldWrapper, AlphafoldResult, AlphaFoldError
from src.alphafold.alphafold_runner import AlphaFoldRunner
from src.alphafold.pdb_processor import PDBProcessor

__all__ = [
    "AlphaFoldWrapper",
    "AlphafoldResult",
    "AlphaFoldError",
    "AlphaFoldRunner",
    "PDBProcessor",
]
