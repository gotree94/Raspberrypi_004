#!/usr/bin/env python
"""
Environment Setup Script
=========================
프로젝트 환경 설정 및 의존성 검증 스크립트.

Usage:
    python scripts/setup_environment.py              # Full setup
    python scripts/setup_environment.py --check-only # Check only
    python scripts/setup_environment.py --install    # Install dependencies
"""

import argparse
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ──────────────────────────────────────────────────────────
# Module Requirements
# ──────────────────────────────────────────────────────────

REQUIRED_MODULES = {
    "numpy": {"import_name": "numpy", "pip": "numpy>=1.21.0", "critical": True},
    "rdkit": {"import_name": "rdkit", "pip": "rdkit (conda install -c conda-forge rdkit)", "critical": True},
    "torch": {"import_name": "torch", "pip": "torch>=1.10.0", "critical": False},
    "scikit-learn": {"import_name": "sklearn", "pip": "scikit-learn>=1.0.0", "critical": False},
    "pandas": {"import_name": "pandas", "pip": "pandas>=1.3.0", "critical": False},
    "matplotlib": {"import_name": "matplotlib", "pip": "matplotlib>=3.4.0", "critical": False},
    "fastapi": {"import_name": "fastapi", "pip": "fastapi>=0.70.0", "critical": False},
    "uvicorn": {"import_name": "uvicorn", "pip": "uvicorn>=0.15.0", "critical": False},
    "py3Dmol": {"import_name": "py3Dmol", "pip": "py3Dmol>=1.8.0", "critical": False},
    "seaborn": {"import_name": "seaborn", "pip": "seaborn>=0.11.0", "critical": False},
    "loguru": {"import_name": "loguru", "pip": "loguru>=0.6.0", "critical": False},
    "pyyaml": {"import_name": "yaml", "pip": "pyyaml>=5.4.0", "critical": False},
}

OPTIONAL_TOOLS = {
    "AutoDock Vina": {
        "check": lambda: shutil.which("vina") is not None,
        "install": "https://github.com/ccsb-scripps/AutoDock-Vina/releases",
    },
    "OpenBabel": {
        "check": lambda: shutil.which("obabel") is not None,
        "install": "conda install -c conda-forge openbabel",
    },
    "ADFR Suite": {
        "check": lambda: (
            shutil.which("prepare_receptor") is not None
            or Path(os.environ.get("ADFR_HOME", ""), "prepare_receptor").exists()
        ),
        "install": "https://ccsb.scripps.edu/adfr/downloads/",
    },
    "Meeko": {
        "check": lambda: _check_module_importable("meeko"),
        "install": "pip install meeko",
    },
}


# ──────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────


def _check_module_importable(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def color(text: str, color_code: str) -> str:
    return f"{color_code}{text}\033[0m"


def green(text: str) -> str:
    return color(text, "\033[92m")


def yellow(text: str) -> str:
    return color(text, "\033[93m")


def red(text: str) -> str:
    return color(text, "\033[91m")


def blue(text: str) -> str:
    return color(text, "\033[94m")


# ──────────────────────────────────────────────────────────
# Check Functions
# ──────────────────────────────────────────────────────────


def check_python_version() -> bool:
    """Check Python version (3.8+)."""
    version = sys.version_info
    ok = version.major == 3 and version.minor >= 8
    if ok:
        print(f"  Python {version.major}.{version.minor}.{version.micro}: {green('OK')}")
    else:
        print(f"  Python {version.major}.{version.minor}.{version.micro}: {red('Need 3.8+')}")
    return ok


def check_pip() -> bool:
    """Check if pip is available."""
    pip_path = shutil.which("pip")
    if pip_path:
        print(f"  pip: {green(f'Found ({pip_path})')}")
        return True
    else:
        print(f"  pip: {red('Not found')}")
        return False


def check_modules() -> dict:
    """Check all required and optional Python modules."""
    results = {"pass": 0, "fail": 0, "critical_fail": 0}

    print(f"\n{'─' * 50}")
    print(blue("Python Modules"))

    for name, info in REQUIRED_MODULES.items():
        import_name = info["import_name"]
        critical = info["critical"]
        found = _check_module_importable(import_name)

        if found:
            try:
                mod = importlib.import_module(import_name)
                version = getattr(mod, "__version__", "unknown")
                print(f"  {name:20s} {green(f'{version:15s}')} OK")
            except Exception:
                print(f"  {name:20s} {green('found')}")
            results["pass"] += 1
        else:
            if critical:
                print(f"  {name:20s} {red('MISSING (CRITICAL)')}")
                results["critical_fail"] += 1
            else:
                print(f"  {name:20s} {yellow('missing (optional)')}")
            results["fail"] += 1

    return results


def check_external_tools() -> dict:
    """Check external tool availability."""
    results = {"found": 0, "not_found": 0}

    print(f"\n{'─' * 50}")
    print(blue("External Tools"))

    for name, info in OPTIONAL_TOOLS.items():
        try:
            found = info["check"]()
        except Exception:
            found = False

        if found:
            print(f"  {name:25s} {green('Found')}")
            results["found"] += 1
        else:
            print(f"  {name:25s} {yellow('Not found')}  (install: {info['install']})")
            results["not_found"] += 1

    return results


def check_directory_structure() -> bool:
    """Check and create project directory structure."""
    print(f"\n{'─' * 50}")
    print(blue("Directory Structure"))

    base = Path(__file__).resolve().parent.parent

    required_dirs = [
        "data/compounds",
        "data/proteins",
        "data/results",
        "data/models",
        "data/configs",
        "data/uploads",
        "notebooks",
    ]

    all_ok = True
    for dir_path in required_dirs:
        full_path = base / dir_path
        if full_path.exists():
            print(f"  {dir_path:30s} {green('OK')}")
        else:
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                print(f"  {dir_path:30s} {yellow('Created')}")
            except Exception as e:
                print(f"  {dir_path:30s} {red(f'Error: {e}')}")
                all_ok = False

    return all_ok


def check_config() -> bool:
    """Validate configuration loading."""
    print(f"\n{'─' * 50}")
    print(blue("Configuration"))

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from src.config import get_config

        cfg = get_config()
        print(f"  Environment:     {cfg.environment}")
        print(f"  AlphaFold:       {cfg.alphafold.backend.value}")
        print(f"  Docking CPU:     {cfg.docking.cpu}")
        print(f"  API:             http://{cfg.api.host}:{cfg.api.port}")
        print(f"  Data directory:  {cfg.data_dir}")
        print(f"  {green('Configuration loaded successfully')}")
        return True
    except Exception as e:
        print(f"  {red(f'Config failed: {e}')}")
        return False


# ──────────────────────────────────────────────────────────
# Install Functions
# ──────────────────────────────────────────────────────────


def install_python_dependencies() -> bool:
    """Install Python dependencies from requirements.txt."""
    print(f"\n{'─' * 50}")
    print(blue("Installing Python Dependencies"))

    req_path = Path(__file__).resolve().parent.parent / "requirements.txt"
    if not req_path.exists():
        print(f"  {red('requirements.txt not found')}")
        return False

    print(f"  Installing from: {req_path}")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            print(f"  {green('Dependencies installed successfully')}")
            return True
        else:
            print(f"  {yellow('Some packages failed:')}")
            for line in proc.stderr.splitlines()[-5:]:
                print(f"    {line}")
            return False
    except Exception as e:
        print(f"  {red(f'Install failed: {e}')}")
        return False


def write_default_config() -> bool:
    """Write a default configuration file."""
    config_dir = Path(__file__).resolve().parent.parent / "data" / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "default.yaml"
    if config_path.exists():
        print(f"  Config already exists: {config_path}")
        return True

    config_content = """
# AI Drug Discovery Automation - Default Configuration
environment: development
seed: 42
verbose: false

alphafold:
  backend: colab
  docker_image: alphafold:latest
  num_models: 5
  use_amber_relax: true

docking:
  vina_path: vina
  cpu: 8
  exhaustiveness: 8
  num_modes: 9

admet:
  use_gpu: false
  ensemble_size: 5
  default_model: random_forest

generation:
  latent_dim: 128
  hidden_dim: 256
  population_size: 100
  mutation_rate: 0.1

pipeline:
  max_parallel_jobs: 4
  retry_max_attempts: 3
  job_timeout_minutes: 120

api:
  host: 0.0.0.0
  port: 8000
  debug: false
"""
    try:
        config_path.write_text(config_content)
        print(f"  {green(f'Default config written: {config_path}')}")
        return True
    except Exception as e:
        print(f"  {red(f'Failed to write config: {e}')}")
        return False


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Setup AI Drug Discovery Automation Environment",
    )
    parser.add_argument(
        "--check-only", "-c",
        action="store_true",
        help="Only check environment, do not install",
    )
    parser.add_argument(
        "--install", "-i",
        action="store_true",
        help="Install missing Python dependencies",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output",
    )
    args = parser.parse_args()

    if not args.quiet:
        print()
        print("=" * 50)
        print("  AI Drug Discovery Automation")
        print("  Environment Setup")
        print("=" * 50)

    results = {}

    # System checks
    results["python"] = check_python_version()
    results["pip"] = check_pip()
    results["directories"] = check_directory_structure()
    results["config"] = check_config()

    # Module checks
    module_results = check_modules()
    results["modules_pass"] = module_results["pass"]
    results["modules_critical_fail"] = module_results["critical_fail"]

    # Tool checks
    tool_results = check_external_tools()
    results["tools_found"] = tool_results["found"]

    # Write default config
    write_default_config()

    # Install if requested
    if args.install and not args.check_only:
        if module_results["fail"] > 0:
            install_python_dependencies()
            print(f"\n  {yellow('Please re-run setup to verify installation.')}")

    # Summary
    if not args.quiet:
        print(f"\n{'=' * 50}")
        print("Summary")
        print(f"{'=' * 50}")
        print(f"  Python version:  {'OK' if results['python'] else 'FAIL'}")
        print(f"  Directories:     {'OK' if results['directories'] else 'FAIL'}")
        print(f"  Config:          {'OK' if results['config'] else 'FAIL'}")
        print(f"  Modules:         {results['modules_pass']} OK, "
              f"{module_results['fail']} missing "
              f"({module_results['critical_fail']} critical)")
        print(f"  External tools:  {results['tools_found']} found, "
              f"{tool_results['not_found']} optional")
        print()

        if module_results["critical_fail"] > 0:
            print(f"  {red('CRITICAL: Some required modules are missing.')}")
            print(f"  {red('Install RDKit: conda install -c conda-forge rdkit')}")
            print(f"  {red('Install others: pip install -r requirements.txt')}")
            print()
            return 1

        if tool_results["not_found"] > 0:
            print(f"  {yellow('Some optional tools are not installed.')}")
            print(f"  {yellow('Install them for full functionality.')}")
            print()

        print(f"  {green('Environment setup complete!')}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
