"""Tests for molecular module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.molecular.rdkit_utils import (
    MolFromSMILES,
    MolToSmiles,
    calculate_all_descriptors,
    is_drug_like,
)


class TestRDKitUtils:
    def test_mol_from_smiles_valid(self):
        """Test valid SMILES parsing."""
        mol = MolFromSMILES("CCO")
        assert mol is not None

    def test_mol_from_smiles_invalid(self):
        """Test invalid SMILES parsing."""
        mol = MolFromSMILES("invalid_smiles")
        assert mol is None

    def test_mol_to_smiles(self):
        """Test SMILES conversion."""
        mol = MolFromSMILES("CCO")
        assert mol is not None
        smiles = MolToSmiles(mol)
        assert isinstance(smiles, str)
        assert len(smiles) > 0

    def test_calculate_all_descriptors(self):
        """Test descriptor calculation."""
        mol = MolFromSMILES("CC(=O)Oc1ccccc1C(=O)O")
        assert mol is not None
        descriptors = calculate_all_descriptors(mol)
        assert isinstance(descriptors, dict)
        assert "MolWt" in descriptors
        assert "MolLogP" in descriptors
        assert "NumHDonors" in descriptors
        assert "NumHAcceptors" in descriptors
        assert "TPSA" in descriptors

    def test_is_drug_like(self):
        """Test drug-likeness check."""
        mol = MolFromSMILES("CC(=O)Oc1ccccc1C(=O)O")
        assert mol is not None
        drug_like, violations = is_drug_like(mol)
        assert isinstance(drug_like, bool)
        assert isinstance(violations, list)


class TestFingerprints:
    def test_fingerprint_generation(self):
        """Test fingerprint generation."""
        from rdkit import Chem
        from src.molecular.fingerprint import FingerprintGenerator

        mol = Chem.MolFromSmiles("CCO")
        assert mol is not None

        gen = FingerprintGenerator()
        fp = gen.morgan_fingerprint(mol)
        assert fp is not None
        assert hasattr(fp, "GetNumBits")

        fp_rdkit = gen.rdkit_fingerprint(mol)
        assert fp_rdkit is not None

    def test_similarity(self):
        """Test similarity calculation."""
        from rdkit import Chem
        from src.molecular.fingerprint import FingerprintGenerator, similarity

        gen = FingerprintGenerator()
        mol1 = Chem.MolFromSmiles("CCO")
        mol2 = Chem.MolFromSmiles("CCO")

        fp1 = gen.morgan_fingerprint(mol1)
        fp2 = gen.morgan_fingerprint(mol2)
        sim = similarity(fp1, fp2)
        assert abs(sim - 1.0) < 0.001  # Same molecule

        mol3 = Chem.MolFromSmiles("c1ccccc1")
        fp3 = gen.morgan_fingerprint(mol3)
        sim_diff = similarity(fp1, fp3)
        assert sim_diff < 1.0  # Different molecules


class TestDescriptors:
    def test_descriptor_calculator(self):
        """Test DescriptorCalculator."""
        from src.molecular.descriptors import DescriptorCalculator
        from rdkit import Chem

        calc = DescriptorCalculator()
        mol = Chem.MolFromSmiles("CCO")
        assert mol is not None

        desc = calc.calculate_all(mol)
        assert isinstance(desc, dict)
        assert len(desc) > 0

        profile = calc.drug_likeness_profile(mol)
        assert isinstance(profile, dict)
        assert "lipinski" in profile
        assert "veber" in profile
