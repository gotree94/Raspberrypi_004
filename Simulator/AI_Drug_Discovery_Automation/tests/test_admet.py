"""Tests for ADMET module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestADMETPredictor:
    def test_predict(self):
        """Test ADMET prediction."""
        from src.admet.predictor import ADMETPredictor

        predictor = ADMETPredictor()
        result = predictor.predict("CC(=O)Oc1ccccc1C(=O)O")

        assert result is not None
        assert hasattr(result, "predictions")
        assert hasattr(result, "aggregate_score")
        assert len(result.predictions) > 0
        assert result.aggregate_score > 0

    def test_predict_invalid_smiles(self):
        """Test prediction with invalid SMILES."""
        from src.admet.predictor import ADMETPredictor

        predictor = ADMETPredictor()
        result = predictor.predict("invalid_smiles")
        assert result.aggregate_score == 0.0
        assert len(result.warnings) > 0


class TestADMETFilters:
    def test_lipinski_filter(self):
        """Test Lipinski rule-of-five filter."""
        from src.admet.filters import apply_filters
        from rdkit import Chem

        mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
        assert mol is not None

        results = apply_filters(mol, ["lipinski"])
        assert "lipinski" in results
        assert isinstance(results["lipinski"], bool)

    def test_veber_filter(self):
        """Test Veber filter."""
        from src.admet.filters import apply_filters
        from rdkit import Chem

        mol = Chem.MolFromSmiles("CCO")
        assert mol is not None

        results = apply_filters(mol, ["veber"])
        assert "veber" in results


class TestADMETModels:
    def test_ensemble_model(self):
        """Test ensemble model creation."""
        from src.admet.models import EnsembleModel, RandomForestModel

        rf = RandomForestModel()
        ensemble = EnsembleModel([rf, rf, rf])
        assert len(ensemble.models) == 3
