"""
Virtual Screening Module
=========================

가상 스크리닝 (Virtual Screening) 모듈.

화합물 라이브러리에서 약물 후보를 발굴하기 위한:
    - 유사도 기반 스크리닝 (Similarity Search)
    - Pharmacophore 기반 스크리닝
    - 화합물 라이브러리 관리
    - 히트 식별 및 클러스터링
"""

from src.screening.similarity_search import (
    SimilaritySearcher,
    HitResult,
    CompoundLibrary,
)

from src.screening.pharmacophore import (
    PharmacophoreGenerator,
    PharmacophoreMatcher,
    Pharmacophore,
    Feature,
)

from src.screening.library_manager import (
    CompoundLibraryManager,
    Compound,
)

__all__ = [
    "SimilaritySearcher", "HitResult", "CompoundLibrary",
    "PharmacophoreGenerator", "PharmacophoreMatcher",
    "Pharmacophore", "Feature",
    "CompoundLibraryManager", "Compound",
]
