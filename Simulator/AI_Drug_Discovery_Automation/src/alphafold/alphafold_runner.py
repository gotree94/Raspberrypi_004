"""
AlphaFold Runner Module
=======================

High-level orchestrator for the complete AlphaFold prediction pipeline.
Manages MSA generation, model inference, relaxation, and result aggregation.
"""

import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from src.alphafold.alphafold_wrapper import (
    AlphaFoldWrapper,
    AlphafoldResult,
    AlphaFoldError,
)
from src.alphafold.pdb_processor import PDBProcessor
from src.config import AlphaFoldConfig, AlphaFoldBackend, get_config

logger = logging.getLogger(__name__)


class AlphaFoldRunner:
    """
    High-level runner for the complete AlphaFold prediction pipeline.

    Manages the full workflow: sequence validation → MSA generation →
    structure prediction → relaxation → confidence extraction → result aggregation.

    Supports batch processing and parallel execution.

    Usage:
        runner = AlphaFoldRunner()
        result = runner.run_pipeline("MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF")
        print(result.mean_plddt)

        # Batch processing
        results = runner.batch_process([
            "MVLSPADKTNVKAAW...",
            "MKFLILFNILVSTLA...",
        ], parallel=True)
    """

    def __init__(
        self,
        config: Optional[AlphaFoldConfig] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ):
        """
        Initialize the AlphaFold runner.

        Args:
            config: AlphaFold configuration.
            progress_callback: Optional progress callback.
        """
        self.config = config or get_config().alphafold
        self.wrapper = AlphaFoldWrapper(
            backend=self.config.backend,
            config=self.config,
            progress_callback=progress_callback,
        )
        self.progress_callback = progress_callback

    def run_pipeline(
        self,
        sequence: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> AlphafoldResult:
        """
        Execute the complete AlphaFold prediction pipeline.

        Pipeline stages:
            1. Sequence validation and preprocessing
            2. MSA generation (if local backend)
            3. Template search
            4. Structure prediction (model inference)
            5. AMBER relaxation
            6. Confidence scoring and result aggregation

        Args:
            sequence: Amino acid sequence.
            options: Optional overrides for prediction parameters.

        Returns:
            AlphafoldResult with complete prediction results.
        """
        options = options or {}
        logger.info(f"Starting AlphaFold pipeline for sequence ({len(sequence)} residues)")

        start_time = time.time()
        self._report_progress("Pipeline initialization", 0.0)

        # Step 1: Sequence validation
        self._report_progress("Validating sequence", 2.0)
        sequence = self._preprocess_sequence(sequence)
        logger.info(f"Sequence length: {len(sequence)} residues")

        # Step 2: Run structure prediction
        self._report_progress("Running structure prediction", 10.0)
        result = self.wrapper.predict_structure(
            sequence=sequence,
            output_dir=options.get("output_dir"),
            job_name=options.get("job_name"),
            num_models=options.get("num_models"),
            use_amber_relax=options.get("use_amber_relax"),
            timeout=options.get("timeout"),
        )

        # Step 3: Post-process results
        if result.success and result.pdb_path:
            self._report_progress("Post-processing results", 90.0)
            result = self._post_process(result)

        elapsed = time.time() - start_time
        result.timing["total_pipeline"] = elapsed
        logger.info(f"Pipeline completed in {elapsed:.1f}s. "
                    f"Mean pLDDT: {result.mean_plddt:.1f}, "
                    f"Grade: {result.get_confidence_grade()}")
        self._report_progress("Pipeline complete", 100.0)

        return result

    def batch_process(
        self,
        sequences: List[str],
        parallel: bool = True,
        max_workers: int = 2,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[AlphafoldResult]:
        """
        Process multiple sequences in batch.

        Args:
            sequences: List of amino acid sequences.
            parallel: Whether to process sequences in parallel.
            max_workers: Maximum number of parallel workers.
            options: Optional overrides for prediction parameters.

        Returns:
            List of AlphafoldResult objects.
        """
        options = options or {}
        results = []

        if parallel and len(sequences) > 1:
            logger.info(f"Batch processing {len(sequences)} sequences (parallel={max_workers})")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {}
                for i, seq in enumerate(sequences):
                    future = executor.submit(
                        self.run_pipeline, seq,
                        {**options, "job_name": options.get("job_name", f"batch_{i}")}
                    )
                    future_map[future] = seq

                for future in as_completed(future_map):
                    seq = future_map[future]
                    try:
                        result = future.result()
                        results.append(result)
                        logger.info(f"Batch complete: {seq[:30]}... → pLDDT {result.mean_plddt:.1f}")
                    except Exception as e:
                        logger.error(f"Batch failed for {seq[:30]}...: {e}")
                        results.append(AlphafoldResult(
                            sequence=seq, success=False, error=str(e)
                        ))
        else:
            for i, seq in enumerate(sequences):
                logger.info(f"Processing sequence {i+1}/{len(sequences)}")
                result = self.run_pipeline(seq, {
                    **options, "job_name": options.get("job_name", f"seq_{i}")
                })
                results.append(result)

        # Sort by confidence
        results.sort(key=lambda r: r.mean_plddt, reverse=True)
        return results

    def _preprocess_sequence(self, sequence: str) -> str:
        """
        Preprocess and validate input sequence.

        Args:
            sequence: Raw amino acid sequence.

        Returns:
            Cleaned and validated sequence.
        """
        # Remove whitespace
        sequence = sequence.strip().upper()

        # Remove non-standard characters (keep standard 20 AAs)
        standard_aas = set("ACDEFGHIKLMNPQRSTVWY")
        cleaned = "".join(c for c in sequence if c in standard_aas)

        if len(cleaned) < len(sequence):
            removed = len(sequence) - len(cleaned)
            logger.warning(f"Removed {removed} non-standard amino acid characters.")

        if len(cleaned) < 5:
            raise ValueError(f"Sequence too short after cleaning: {len(cleaned)} residues.")

        return cleaned

    def _post_process(self, result: AlphafoldResult) -> AlphafoldResult:
        """
        Post-process prediction results.

        Args:
            result: Raw AlphafoldResult.

        Returns:
            Enhanced AlphafoldResult with additional metrics.
        """
        if not result.pdb_path or not Path(result.pdb_path).exists():
            return result

        try:
            # Extract additional metrics using PDBProcessor
            processor = PDBProcessor()

            # Get detailed structure metrics
            metrics = processor.get_structure_metrics(result.pdb_path)
            result.metadata.update(metrics)

            # Extract confidence scores if not already present
            if result.plddt_scores is None or len(result.plddt_scores) == 0:
                scores = processor.extract_confidence_scores(result.pdb_path)
                if len(scores) > 0:
                    result.plddt_scores = scores
                    result.mean_plddt = float(np.mean(scores))

            # Calculate predicted RMSD from PAE
            if result.pae_matrix is not None:
                n = result.pae_matrix.shape[0]
                # Predicted RMSD ≈ sqrt(mean(PAE²))
                rmsd_estimate = float(np.sqrt(np.mean(result.pae_matrix ** 2)))
                result.predicted_rmsd = rmsd_estimate

        except Exception as e:
            logger.warning(f"Post-processing error: {e}")

        return result

    def _report_progress(self, stage: str, progress: float) -> None:
        """Report progress via callback if set."""
        if self.progress_callback:
            self.progress_callback(stage, progress)
        logger.debug(f"Pipeline progress: {stage} ({progress:.1f}%)")

    def generate_report(self, result: AlphafoldResult, output_path: str) -> str:
        """
        Generate a structured report of the prediction results.

        Args:
            result: AlphafoldResult to report.
            output_path: Path to write the report.

        Returns:
            Path to the generated report.
        """
        report_lines = [
            "=" * 60,
            "AlphaFold Structure Prediction Report",
            "=" * 60,
            "",
            f"Sequence: {result.sequence[:50]}... ({len(result.sequence)} residues)",
            f"Mean pLDDT: {result.mean_plddt:.1f}",
            f"Confidence Grade: {result.get_confidence_grade()}",
            f"Max PAE: {result.max_pae:.1f}",
            f"Predicted RMSD: {result.predicted_rmsd:.2f}" if result.predicted_rmsd else "",
            "",
            "-" * 40,
            "Per-residue pLDDT Distribution",
            "-" * 40,
            f"  Very High (pLDDT > 90): {sum(1 for s in (result.plddt_scores or []) if s > 90)} residues",
            f"  Confident (pLDDT 70-90): {sum(1 for s in (result.plddt_scores or []) if 70 <= s <= 90)} residues",
            f"  Low (pLDDT 50-70): {sum(1 for s in (result.plddt_scores or []) if 50 <= s < 70)} residues",
            f"  Very Low (pLDDT < 50): {sum(1 for s in (result.plddt_scores or []) if s < 50)} residues",
            "",
            "-" * 40,
            "Output Files",
            "-" * 40,
            f"  PDB (relaxed): {result.pdb_path or 'N/A'}",
            f"  PDB (unrelaxed): {result.unrelaxed_pdb_path or 'N/A'}",
            "",
            "-" * 40,
            "Timing",
            "-" * 40,
        ]
        for stage, duration in result.timing.items():
            report_lines.append(f"  {stage}: {duration:.1f}s")

        report_lines.extend([
            "",
            "-" * 40,
            "Metadata",
            "-" * 40,
        ])
        for key, value in result.metadata.items():
            report_lines.append(f"  {key}: {value}")

        report_lines.append("")
        report_lines.append("=" * 60)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(report_lines), encoding="utf-8")

        logger.info(f"Report saved to: {output_path}")
        return str(output_path)
