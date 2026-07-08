"""
Molecular Processing Module
============================

RDKit 기반 분자 처리, 지문(Fingerprint) 계산, 기술자(Descriptor) 추출 모듈.

Supports:
    - SMILES/SDF 분자 입출력 및 검증
    - 30+ 분자 기술자 계산 (MW, LogP, HBD, HBA, TPSA, RotB 등)
    - 다양한 지문 방식 (Morgan/ECFP, MACCS, Topological, Pharmacophore)
    - 분자 유사도 계산 (Tanimoto, Dice, Cosine)
    - 약물성 필터 (Lipinski, Veber, Ghose)
"""

from src.molecular.rdkit_utils import (
    MolFromSMILES,
    MolFromSDF,
    MolToSMILES,
    MolToSDF,
    sanitize_molecule,
    get_molecule_image,
    standardize_smiles,
    is_valid_smiles,
    calculate_mw,
    calculate_logp,
    calculate_hbd,
    calculate_hba,
    calculate_tpsa,
    calculate_rotatable_bonds,
    calculate_all_descriptors,
    get_molecular_formula,
    get_molecular_weight_exact,
    get_num_rings,
    get_aromatic_rings,
    detect_functional_groups,
    conformer_generation,
    embed_molecule,
)

from src.molecular.fingerprint import (
    MorganFingerprintGenerator,
    MACCSFingerprintGenerator,
    TopologicalFingerprintGenerator,
    PharmacophoreFingerprintGenerator,
    AtomPairFingerprintGenerator,
    RDKitFingerprintGenerator,
    FingerprintManager,
    tanimoto_similarity,
    dice_similarity,
    cosine_similarity,
    compute_similarity_matrix,
    nearest_neighbors,
)

from src.molecular.descriptors import (
    DescriptorCalculator,
    lipinski_rule_of_five,
    veber_rule,
    ghose_filter,
    lead_likeness_filter,
    batch_calculate,
)

__all__ = [
    "MolFromSMILES", "MolFromSDF", "MolToSMILES", "MolToSDF",
    "sanitize_molecule", "get_molecule_image", "standardize_smiles",
    "is_valid_smiles", "calculate_all_descriptors",
    "calculate_mw", "calculate_logp", "calculate_hbd", "calculate_hba",
    "calculate_tpsa", "calculate_rotatable_bonds",
    "get_molecular_formula", "get_molecular_weight_exact",
    "get_num_rings", "get_aromatic_rings", "detect_functional_groups",
    "conformer_generation", "embed_molecule",
    "MorganFingerprintGenerator", "MACCSFingerprintGenerator",
    "TopologicalFingerprintGenerator", "PharmacophoreFingerprintGenerator",
    "AtomPairFingerprintGenerator", "RDKitFingerprintGenerator",
    "FingerprintManager",
    "tanimoto_similarity", "dice_similarity", "cosine_similarity",
    "compute_similarity_matrix", "nearest_neighbors",
    "DescriptorCalculator", "lipinski_rule_of_five", "veber_rule",
    "ghose_filter", "lead_likeness_filter", "batch_calculate",
]
