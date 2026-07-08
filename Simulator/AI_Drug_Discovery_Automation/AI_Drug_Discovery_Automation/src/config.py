"""
Project Configuration Module
============================

Centralized configuration management with dataclasses,
environment variable loading, and YAML config file support.
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from enum import Enum


# ──────────────────────────────────────────────────────────
# Base Paths
# ──────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = DATA_DIR / "models"
RESULT_DIR = DATA_DIR / "results"
COMPOUND_DIR = DATA_DIR / "compounds"
PROTEIN_DIR = DATA_DIR / "proteins"
CONFIG_DIR = DATA_DIR / "configs"
NOTEBOOK_DIR = BASE_DIR / "notebooks"
SCRIPTS_DIR = BASE_DIR / "scripts"

# ──────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────


class AlphaFoldBackend(Enum):
    LOCAL = "local"
    DOCKER = "docker"
    COLAB = "colab"
    LOCAL_ALPHAFOLD3 = "alphafold3"


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ──────────────────────────────────────────────────────────
# Configuration Dataclasses
# ──────────────────────────────────────────────────────────


@dataclass
class AlphaFoldConfig:
    """AlphaFold integration configuration."""
    backend: AlphaFoldBackend = AlphaFoldBackend.COLAB
    docker_image: str = "alphafold:latest"
    docker_gpu: bool = True
    local_alphafold_dir: str = ""
    colab_url: str = "https://colab.research.google.com/github/deepmind/alphafold/blob/main/AlphaFold.ipynb"
    max_template_date: str = "2024-01-01"
    num_models: int = 5
    use_amber_relax: bool = True
    output_dir: str = str(PROTEIN_DIR)
    data_dir: str = str(DATA_DIR / "alphafold_data")
    timeout_minutes: int = 60


@dataclass
class DockingConfig:
    """AutoDock Vina configuration."""
    vina_path: str = "vina"
    vina_score_only: bool = False
    cpu: int = 8
    exhaustiveness: int = 8
    num_modes: int = 9
    energy_range: float = 3.0
    spacing: float = 1.0
    output_dir: str = str(RESULT_DIR / "docking")
    prepare_receptor_path: str = "prepare_receptor"
    prepare_ligand_path: str = "prepare_ligand"


@dataclass
class ADMETConfig:
    """ADMET prediction configuration."""
    model_dir: str = str(MODEL_DIR / "admet")
    use_gpu: bool = False
    ensemble_size: int = 5
    cache_predictions: bool = True
    default_model: str = "random_forest"
    prediction_threshold: float = 0.5


@dataclass
class GenerationConfig:
    """Molecular generation configuration."""
    latent_dim: int = 128
    hidden_dim: int = 256
    vocab_size: int = 40
    max_smiles_length: int = 100
    batch_size: int = 64
    learning_rate: float = 1e-3
    num_epochs: int = 100
    model_dir: str = str(MODEL_DIR / "generation")
    temperature: float = 1.0
    population_size: int = 100
    mutation_rate: float = 0.1


@dataclass
class PipelineConfig:
    """Pipeline orchestration configuration."""
    max_iterations: int = 10
    convergence_threshold: float = 0.1
    max_parallel_jobs: int = 4
    checkpoint_dir: str = str(RESULT_DIR / "checkpoints")
    log_dir: str = str(RESULT_DIR / "logs")
    retry_max_attempts: int = 3
    retry_backoff_factor: float = 2.0
    job_timeout_minutes: int = 120


@dataclass
class APIConfig:
    """REST API configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list = field(default_factory=lambda: ["*"])
    debug: bool = False
    api_prefix: str = "/api"
    max_upload_size_mb: int = 100
    rate_limit_per_minute: int = 60
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: LogLevel = LogLevel.INFO
    file: str = str(RESULT_DIR / "logs" / "app.log")
    format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}"
    rotation: str = "1 day"
    retention: str = "30 days"


@dataclass
class AppConfig:
    """Root application configuration."""
    environment: str = "development"
    data_dir: str = str(DATA_DIR)
    result_dir: str = str(RESULT_DIR)
    model_dir: str = str(MODEL_DIR)
    seed: int = 42
    verbose: bool = False

    alphafold: AlphaFoldConfig = field(default_factory=AlphaFoldConfig)
    docking: DockingConfig = field(default_factory=DockingConfig)
    admet: ADMETConfig = field(default_factory=ADMETConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


# ──────────────────────────────────────────────────────────
# Config Manager
# ──────────────────────────────────────────────────────────


class ConfigManager:
    """
    Manages application configuration with support for:
    - Default dataclass values
    - YAML/JSON configuration files
    - Environment variable overrides
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = AppConfig()
        if config_path and Path(config_path).exists():
            self.load_from_file(config_path)
        self._apply_env_overrides()
        self._ensure_directories()

    def load_from_file(self, path: str) -> None:
        """Load configuration from a JSON or YAML file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        content = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                raise ImportError("PyYAML is required for YAML config files. pip install pyyaml")
        elif p.suffix == ".json":
            data = json.loads(content)
        else:
            raise ValueError(f"Unsupported config file format: {p.suffix}")

        self._update_dataclass(self.config, data)

    def _update_dataclass(self, obj: Any, data: Dict) -> None:
        """Recursively update a dataclass instance from a dictionary."""
        for key, value in data.items():
            if hasattr(obj, key):
                field_value = getattr(obj, key)
                if isinstance(field_value, (AlphaFoldConfig, DockingConfig, ADMETConfig,
                                           GenerationConfig, PipelineConfig, APIConfig, LoggingConfig)):
                    self._update_dataclass(field_value, value)
                else:
                    setattr(obj, key, value)

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides (prefix: AI_DRUG_)."""
        prefix = "AI_DRUG_"
        for env_key, env_val in os.environ.items():
            if env_key.startswith(prefix):
                # Parse nested config path: AI_DRUG_ALPHAFOLD_BACKEND → config.alphafold.backend
                parts = env_key[len(prefix):].lower().split("_")
                if len(parts) >= 2:
                    section = parts[0]
                    field = "_".join(parts[1:])
                    if hasattr(self.config, section):
                        section_obj = getattr(self.config, section)
                        if hasattr(section_obj, field):
                            # Type conversion
                            current_val = getattr(section_obj, field)
                            if isinstance(current_val, bool):
                                env_val = env_val.lower() in ("true", "1", "yes")
                            elif isinstance(current_val, int):
                                env_val = int(env_val)
                            elif isinstance(current_val, float):
                                env_val = float(env_val)
                            try:
                                setattr(section_obj, field, type(current_val)(env_val))
                            except (ValueError, TypeError):
                                pass

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        for dir_path in [
            DATA_DIR, MODEL_DIR, RESULT_DIR, COMPOUND_DIR, PROTEIN_DIR, CONFIG_DIR,
            Path(self.config.alphafold.output_dir),
            Path(self.config.alphafold.data_dir),
            Path(self.config.docking.output_dir),
            Path(self.config.admet.model_dir),
            Path(self.config.generation.model_dir),
            Path(self.config.pipeline.checkpoint_dir),
            Path(self.config.pipeline.log_dir),
            Path(self.config.logging.file).parent,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict:
        """Export configuration as a dictionary."""
        return asdict(self.config)

    def save(self, path: str) -> None:
        """Save configuration to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def get_logging_config(self) -> Dict:
        """Get logging configuration dictionary."""
        return {
            "level": self.config.logging.level.value,
            "file": self.config.logging.file,
            "format": self.config.logging.format,
            "rotation": self.config.logging.rotation,
            "retention": self.config.logging.retention,
        }

    def __repr__(self) -> str:
        return f"ConfigManager(environment={self.config.environment})"


# ──────────────────────────────────────────────────────────
# Global singleton instance
# ──────────────────────────────────────────────────────────

_config_manager: Optional[ConfigManager] = None


def get_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Get the global configuration instance.

    Args:
        config_path: Optional path to a configuration file.

    Returns:
        AppConfig singleton instance.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager.config


def setup_logging(config: Optional[AppConfig] = None) -> None:
    """
    Set up logging with the specified configuration.

    Args:
        config: Application configuration. Uses global config if None.
    """
    cfg = config or get_config()
    log_cfg = cfg.logging

    try:
        from loguru import logger
        logger.remove()  # Remove default handler

        # Console handler
        logger.add(
            lambda msg: print(msg, end=""),
            level=log_cfg.level.value,
            format=log_cfg.format,
            colorize=True,
        )

        # File handler
        log_path = Path(log_cfg.file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_path),
            level=log_cfg.level.value,
            format=log_cfg.format,
            rotation=log_cfg.rotation,
            retention=log_cfg.retention,
            compression="gz",
        )

        logger.info(f"Logging configured: level={log_cfg.level.value}, file={log_cfg.file}")
    except ImportError:
        # Fallback to standard logging
        logging.basicConfig(
            level=getattr(logging, log_cfg.level.value, logging.INFO),
            format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_cfg.file) if log_cfg.file else logging.NullHandler(),
            ],
        )
        logging.getLogger().info(f"Standard logging configured (loguru not available)")


# ──────────────────────────────────────────────────────────
# Quick test
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    cfg = get_config()
    print("=== AI Drug Discovery Configuration ===")
    print(f"Environment: {cfg.environment}")
    print(f"AlphaFold backend: {cfg.alphafold.backend.value}")
    print(f"Docking CPU cores: {cfg.docking.cpu}")
    print(f"API endpoint: http://{cfg.api.host}:{cfg.api.port}")
    print(f"Data directory: {cfg.data_dir}")
    print(f"Model directory: {cfg.model_dir}")
