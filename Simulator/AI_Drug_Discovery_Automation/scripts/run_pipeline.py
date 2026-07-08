#!/usr/bin/env python
"""
Pipeline Execution Script
==========================
명령줄에서 신약 개발 파이프라인을 실행하는 진입점.

Usage:
    python scripts/run_pipeline.py --target <protein_sequence> --workflow full
    python scripts/run_pipeline.py --workflow docking --receptor receptor.pdb --ligands ligands.smi
    python scripts/run_pipeline.py --list-workflows
    python scripts/run_pipeline.py --workflow generation --seeds smiles.txt --num 100
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any


# ──────────────────────────────────────────────────────────
# Argument Parser
# ──────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Drug Discovery Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_pipeline.py --target "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF" --workflow full
  python scripts/run_pipeline.py --workflow docking --receptor data/proteins/1a42.pdb --ligands data/compounds/library.smi
  python scripts/run_pipeline.py --workflow generation --seeds data/compounds/seeds.smi --num 100
        """,
    )

    parser.add_argument(
        "--workflow", "-w",
        type=str,
        default="full",
        help="Workflow template name (full, docking, generation, screening)",
    )
    parser.add_argument(
        "--target", "-t",
        type=str,
        help="Protein target amino acid sequence (for AlphaFold prediction)",
    )
    parser.add_argument(
        "--receptor", "-r",
        type=str,
        help="Path to receptor PDB file",
    )
    parser.add_argument(
        "--ligands", "-l",
        type=str,
        help="Path to ligand SMILES file (one per line)",
    )
    parser.add_argument(
        "--seeds", "-s",
        type=str,
        help="Path to seed SMILES file for generation",
    )
    parser.add_argument(
        "--num", "-n",
        type=int,
        default=100,
        help="Number of molecules to generate (default: 100)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory for results",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (JSON or YAML)",
    )
    parser.add_argument(
        "--list-workflows",
        action="store_true",
        help="List available workflow templates",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate pipeline setup without executing",
    )

    return parser


# ──────────────────────────────────────────────────────────
# Pipeline Runner
# ──────────────────────────────────────────────────────────


def setup_environment(config_path: Optional[str] = None) -> Any:
    """Initialize configuration and logging."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from src.config import get_config, setup_logging

    cfg = get_config(config_path)
    setup_logging(cfg)

    if cfg.verbose:
        print(f"Configuration loaded: {cfg.environment}")
        print(f"Data directory: {cfg.data_dir}")
        print(f"Model directory: {cfg.model_dir}")

    return cfg


def run_full_pipeline(target_sequence: str, config_path: Optional[str] = None) -> Dict:
    """Run the complete end-to-end drug discovery pipeline."""
    from src.pipeline.workflow_manager import WorkflowManager
    from src.config import get_config

    cfg = get_config(config_path)
    wf_manager = WorkflowManager()

    workflow = WorkflowManager.full_pipeline()
    orchestrator = wf_manager.create_orchestrator(workflow)

    pipeline_id = f"full_{int(time.time())}"
    inputs = {"target_sequence": target_sequence}

    print(f"Starting full pipeline: {pipeline_id}")
    print(f"Target sequence: {target_sequence[:50]}...")

    context = orchestrator.run(inputs=inputs, pipeline_id=pipeline_id)

    report = orchestrator.get_report()
    print(f"\nPipeline completed: {report['status']}")
    print(f"Total runtime: {report['total_runtime']:.2f}s")
    print(f"Stages: {report['completed_stages']}/{report['num_stages']} completed")

    return report


def run_docking_pipeline(
    receptor_pdb: str,
    ligands_file: str,
    config_path: Optional[str] = None,
) -> Dict:
    """Run the docking-only pipeline."""
    from src.pipeline.workflow_manager import WorkflowManager
    from src.config import get_config

    cfg = get_config(config_path)
    wf_manager = WorkflowManager()

    workflow = WorkflowManager.docking_only()
    orchestrator = wf_manager.create_orchestrator(workflow)

    pipeline_id = f"docking_{int(time.time())}"
    inputs = {
        "receptor_pdb": receptor_pdb,
        "ligands_file": ligands_file,
    }

    print(f"Starting docking pipeline: {pipeline_id}")
    print(f"Receptor: {receptor_pdb}")
    print(f"Ligands: {ligands_file}")

    context = orchestrator.run(inputs=inputs, pipeline_id=pipeline_id)

    report = orchestrator.get_report()
    print(f"\nPipeline completed: {report['status']}")
    return report


def run_generation_pipeline(
    seeds_file: str,
    num_molecules: int = 100,
    config_path: Optional[str] = None,
) -> Dict:
    """Run the molecular generation pipeline."""
    from src.pipeline.workflow_manager import WorkflowManager
    from src.config import get_config

    cfg = get_config(config_path)
    wf_manager = WorkflowManager()

    workflow = WorkflowManager.generation_only()
    orchestrator = wf_manager.create_orchestrator(workflow)

    pipeline_id = f"generation_{int(time.time())}"
    inputs = {
        "seeds_file": seeds_file,
        "num_molecules": num_molecules,
    }

    print(f"Starting generation pipeline: {pipeline_id}")
    print(f"Seeds: {seeds_file}")
    print(f"Target molecules: {num_molecules}")

    context = orchestrator.run(inputs=inputs, pipeline_id=pipeline_id)

    report = orchestrator.get_report()
    print(f"\nPipeline completed: {report['status']}")
    return report


def run_screening_pipeline(config_path: Optional[str] = None) -> Dict:
    """Run the virtual screening pipeline."""
    from src.pipeline.workflow_manager import WorkflowManager
    from src.config import get_config

    cfg = get_config(config_path)
    wf_manager = WorkflowManager()

    workflow = WorkflowManager.screening_pipeline()
    orchestrator = wf_manager.create_orchestrator(workflow)

    pipeline_id = f"screening_{int(time.time())}"

    print(f"Starting screening pipeline: {pipeline_id}")

    context = orchestrator.run(inputs={}, pipeline_id=pipeline_id)

    report = orchestrator.get_report()
    print(f"\nPipeline completed: {report['status']}")
    return report


# ──────────────────────────────────────────────────────────
# Dry Run
# ──────────────────────────────────────────────────────────


def dry_run(args: argparse.Namespace) -> None:
    """Validate pipeline configuration without execution."""
    print("=" * 60)
    print("DRY RUN - Validating Pipeline Configuration")
    print("=" * 60)

    print(f"\nWorkflow: {args.workflow}")
    print(f"Config: {args.config or 'default'}")

    workflows = ["full", "docking", "generation", "screening"]
    if args.workflow not in workflows:
        print(f"ERROR: Unknown workflow '{args.workflow}'")
        print(f"Available: {', '.join(workflows)}")
        sys.exit(1)

    if args.workflow == "full" and not args.target:
        print("WARNING: No target sequence provided. AlphaFold stage will be skipped.")

    if args.workflow == "docking":
        if not args.receptor:
            print("ERROR: Docking workflow requires --receptor")
            sys.exit(1)
        if not args.ligands:
            print("ERROR: Docking workflow requires --ligands")
            sys.exit(1)

    if args.workflow == "generation" and not args.seeds:
        print("ERROR: Generation workflow requires --seeds")
        sys.exit(1)

    print("\nConfiguration looks valid!")
    print("Use --dry-run to remove this flag and execute.")


def list_workflows() -> None:
    """List available workflow templates."""
    from src.pipeline.workflow_manager import WorkflowManager

    templates = WorkflowManager.list_templates()
    print("\nAvailable Workflow Templates:")
    print("=" * 50)
    for name, description in templates.items():
        print(f"  {name:20s}  {description}")
    print()


# ──────────────────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────────────────


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Setup
    cfg = setup_environment(args.config)

    if args.list_workflows:
        list_workflows()
        return

    if args.dry_run:
        dry_run(args)
        return

    if args.output:
        cfg.result_dir = args.output

    # Execute pipeline
    start_time = time.time()

    try:
        if args.workflow == "full":
            if not args.target:
                print("ERROR: Full pipeline requires --target (protein sequence)")
                sys.exit(1)
            report = run_full_pipeline(args.target, args.config)

        elif args.workflow == "docking":
            if not args.receptor or not args.ligands:
                print("ERROR: Docking pipeline requires --receptor and --ligands")
                sys.exit(1)
            report = run_docking_pipeline(args.receptor, args.ligands, args.config)

        elif args.workflow == "generation":
            if not args.seeds:
                print("ERROR: Generation pipeline requires --seeds")
                sys.exit(1)
            report = run_generation_pipeline(args.seeds, args.num, args.config)

        elif args.workflow == "screening":
            report = run_screening_pipeline(args.config)

        else:
            print(f"Unknown workflow: {args.workflow}")
            list_workflows()
            sys.exit(1)

        total_time = time.time() - start_time
        print(f"\nTotal execution time: {total_time:.2f}s")

        # Save report
        if report:
            output_path = Path(cfg.result_dir) / f"pipeline_report_{int(start_time)}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to: {output_path}")

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nPipeline failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
