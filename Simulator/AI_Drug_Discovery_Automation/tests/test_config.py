"""Tests for configuration module."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    get_config,
    ConfigManager,
    AppConfig,
    AlphaFoldConfig,
    DockingConfig,
    GenerationConfig,
    AlphaFoldBackend,
)


class TestConfigManager:
    def test_default_config(self):
        """Test default configuration creation."""
        config = get_config()
        assert config is not None
        assert config.environment == "development"
        assert config.seed == 42

    def test_alphafold_config(self):
        """Test AlphaFold configuration defaults."""
        config = get_config()
        assert config.alphafold.backend == AlphaFoldBackend.COLAB
        assert config.alphafold.num_models == 5
        assert config.alphafold.use_amber_relax is True

    def test_docking_config(self):
        """Test docking configuration defaults."""
        config = get_config()
        assert config.docking.cpu == 8
        assert config.docking.exhaustiveness == 8
        assert config.docking.num_modes == 9

    def test_generation_config(self):
        """Test generation configuration defaults."""
        config = get_config()
        assert config.generation.latent_dim == 128
        assert config.generation.hidden_dim == 256
        assert config.generation.population_size == 100

    def test_env_override(self):
        """Test environment variable override."""
        os.environ["AI_DRUG_ALPHAFOLD_BACKEND"] = "local"
        os.environ["AI_DRUG_DOCKING_CPU"] = "4"

        config = get_config()
        assert config.alphafold.backend == AlphaFoldBackend.LOCAL
        assert config.docking.cpu == 4

        # Cleanup
        del os.environ["AI_DRUG_ALPHAFOLD_BACKEND"]
        del os.environ["AI_DRUG_DOCKING_CPU"]

    def test_config_to_dict(self):
        """Test config serialization."""
        manager = ConfigManager()
        d = manager.to_dict()
        assert isinstance(d, dict)
        assert "environment" in d
        assert "alphafold" in d
        assert "docking" in d

    def test_config_save_load_json(self):
        """Test config save/load."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write('{"environment": "testing", "seed": 123}')
            temp_path = f.name

        manager = ConfigManager(temp_path)
        assert manager.config.environment == "testing"
        assert manager.config.seed == 123

        os.unlink(temp_path)
