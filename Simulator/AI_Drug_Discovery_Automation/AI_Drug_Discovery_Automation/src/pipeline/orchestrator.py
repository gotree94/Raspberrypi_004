"""
Pipeline Orchestrator
======================
DAG 기반 파이프라인 실행 엔진.
단계별 의존성을 관리하고 병렬 실행 및 체크포인트를 지원합니다.
"""

import asyncio
import time
import traceback
from typing import Optional, List, Dict, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Enums & Data Structures
# ──────────────────────────────────────────────────────────


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PipelineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StageResult:
    """Result of a single pipeline stage execution."""
    stage_name: str
    status: StageStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    runtime_seconds: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "error": self.error,
            "runtime_seconds": self.runtime_seconds,
        }


@dataclass
class Stage:
    """A single stage in the pipeline DAG."""
    name: str
    description: str = ""
    depends_on: List[str] = field(default_factory=list)
    timeout_minutes: int = 60
    retry_attempts: int = 0
    retry_delay_seconds: int = 5

    # The actual function to execute
    handler: Optional[Callable] = None
    handler_kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """Execution context passed through pipeline stages."""
    pipeline_id: str
    config: Any = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    stage_results: Dict[str, StageResult] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)


class PipelineOrchestrator:
    """
    DAG-based pipeline orchestrator.

    Manages execution of dependent stages with:
    - Automatic dependency resolution
    - Parallel execution of independent stages
    - Checkpoint/restart support
    - Error handling and retry
    - Progress tracking and reporting
    """

    def __init__(self, config: Optional[Any] = None):
        cfg = config or get_config()
        pipe_cfg = cfg.pipeline
        self.config = cfg

        self.max_parallel_jobs = pipe_cfg.max_parallel_jobs
        self.retry_max_attempts = pipe_cfg.retry_max_attempts
        self.retry_backoff_factor = pipe_cfg.retry_backoff_factor
        self.checkpoint_dir = Path(pipe_cfg.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(pipe_cfg.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.stages: Dict[str, Stage] = {}
        self.context: Optional[PipelineContext] = None
        self.status: PipelineStatus = PipelineStatus.IDLE
        self._cancel_requested = False

    # ──────────────────────────────────────────────────────────
    # Stage Registration
    # ──────────────────────────────────────────────────────────

    def add_stage(self, stage: Stage) -> "PipelineOrchestrator":
        """Register a pipeline stage."""
        if stage.name in self.stages:
            raise ValueError(f"Stage '{stage.name}' already exists")
        self.stages[stage.name] = stage
        return self

    def add_stages(self, stages: List[Stage]) -> "PipelineOrchestrator":
        """Register multiple stages at once."""
        for stage in stages:
            self.add_stage(stage)
        return self

    def remove_stage(self, name: str) -> None:
        """Remove a stage by name."""
        self.stages.pop(name, None)

    def get_stage(self, name: str) -> Optional[Stage]:
        """Get a stage by name."""
        return self.stages.get(name)

    def get_stage_result(self, name: str) -> Optional[StageResult]:
        """Get the result of a completed stage."""
        if self.context and name in self.context.stage_results:
            return self.context.stage_results[name]
        return None

    # ──────────────────────────────────────────────────────────
    # DAG Resolution
    # ──────────────────────────────────────────────────────────

    def _get_execution_order(self) -> List[List[str]]:
        """
        Topological sort of stages into parallel execution layers.

        Returns:
            List of layers, where each layer is a list of stage names
            that can run in parallel.
        """
        # Build dependency graph
        dependents: Dict[str, Set[str]] = {name: set() for name in self.stages}
        for name, stage in self.stages.items():
            for dep in stage.depends_on:
                if dep in dependents:
                    dependents[name].add(dep)

        # Kahn's algorithm for topological ordering
        in_degree = {name: len(deps) for name, deps in dependents.items()}
        layers = []

        remaining = set(self.stages.keys())
        while remaining:
            # Find stages with no remaining dependencies
            ready = [n for n in remaining if in_degree.get(n, 0) == 0]
            if not ready:
                # Cycle detected
                cycle = [n for n in remaining if in_degree.get(n, 0) > 0]
                raise ValueError(f"Circular dependency detected: {cycle}")

            layers.append(ready)
            for name in ready:
                # Update dependents
                for other in remaining:
                    if name in dependents.get(other, set()):
                        in_degree[other] -= 1
                remaining.remove(name)

        return layers

    def validate_dag(self) -> List[str]:
        """
        Validate the DAG for cycles and missing dependencies.

        Returns:
            List of validation warnings/errors
        """
        errors = []

        # Check for missing dependencies
        for name, stage in self.stages.items():
            for dep in stage.depends_on:
                if dep not in self.stages:
                    errors.append(f"Stage '{name}' depends on missing stage '{dep}'")

        # Check for cycles
        try:
            self._get_execution_order()
        except ValueError as e:
            errors.append(str(e))

        return errors

    # ──────────────────────────────────────────────────────────
    # Pipeline Execution
    # ──────────────────────────────────────────────────────────

    async def run_async(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        pipeline_id: Optional[str] = None,
        start_stage: Optional[str] = None,
        end_stage: Optional[str] = None,
    ) -> PipelineContext:
        """
        Run the pipeline asynchronously.

        Args:
            inputs: Input parameters for the pipeline
            pipeline_id: Optional pipeline ID (auto-generated if None)
            start_stage: Stage to start from (for resume)
            end_stage: Stage to stop after

        Returns:
            PipelineContext with all stage results
        """
        if pipeline_id is None:
            pipeline_id = f"pipeline_{int(time.time())}"

        self.context = PipelineContext(
            pipeline_id=pipeline_id,
            config=self.config,
            inputs=inputs or {},
        )
        self.status = PipelineStatus.RUNNING
        self._cancel_requested = False

        # Load checkpoint if resuming
        if start_stage and self._load_checkpoint(pipeline_id):
            # Resume from checkpoint
            pass

        execution_layers = self._get_execution_order()

        try:
            for layer in execution_layers:
                if self._cancel_requested:
                    self.status = PipelineStatus.CANCELLED
                    break

                # Filter to stages within range
                active_stages = []
                for stage_name in layer:
                    stage = self.stages[stage_name]

                    # Skip if already completed (resume mode)
                    if (stage_name in self.context.stage_results
                            and self.context.stage_results[stage_name].status == StageStatus.COMPLETED):
                        continue

                    if start_stage and stage_name not in self._get_stage_set(start_stage):
                        continue
                    if end_stage and stage_name not in self._get_stage_set(end_stage, reverse=True):
                        continue

                    active_stages.append(stage)

                if not active_stages:
                    continue

                # Run stages in parallel
                tasks = [self._run_single_stage(s) for s in active_stages]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check for failures
                for stage, result in zip(active_stages, results):
                    if isinstance(result, Exception):
                        stage_result = StageResult(
                            stage_name=stage.name,
                            status=StageStatus.FAILED,
                            error=f"{type(result).__name__}: {str(result)}",
                        )
                        self.context.stage_results[stage.name] = stage_result

                # Save checkpoint after each layer
                self._save_checkpoint(pipeline_id)

                # Stop on failure (unless stages handle their own errors)
                failed_stages = [
                    s for s in active_stages
                    if self.context.stage_results.get(s.name, StageResult(s.name, StageStatus.FAILED)).status == StageStatus.FAILED
                ]
                if failed_stages:
                    self.status = PipelineStatus.FAILED
                    break

            if self.status == PipelineStatus.RUNNING:
                self.status = PipelineStatus.COMPLETED

        except Exception as e:
            self.status = PipelineStatus.FAILED
            if self.context:
                self.context.shared_data["_pipeline_error"] = str(e)
                self.context.shared_data["_pipeline_traceback"] = traceback.format_exc()

        return self.context

    def run(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        pipeline_id: Optional[str] = None,
        start_stage: Optional[str] = None,
        end_stage: Optional[str] = None,
    ) -> PipelineContext:
        """
        Synchronous pipeline execution.

        Args:
            inputs: Input parameters
            pipeline_id: Optional pipeline ID
            start_stage: Stage to start from
            end_stage: Stage to stop after

        Returns:
            PipelineContext
        """
        return asyncio.run(self.run_async(inputs, pipeline_id, start_stage, end_stage))

    async def _run_single_stage(self, stage: Stage) -> StageResult:
        """Execute a single pipeline stage with retry logic."""
        start_time = time.time()
        last_error = None

        for attempt in range(1 + stage.retry_attempts):
            if self._cancel_requested:
                return StageResult(
                    stage_name=stage.name,
                    status=StageStatus.CANCELLED,
                    runtime_seconds=time.time() - start_time,
                )

            try:
                stage_start = time.time()
                result = StageResult(
                    stage_name=stage.name,
                    status=StageStatus.RUNNING,
                    start_time=stage_start,
                )

                # Execute the handler
                if stage.handler:
                    # Collect dependencies' outputs as inputs
                    dep_outputs = {}
                    for dep in stage.depends_on:
                        if dep in self.context.stage_results:
                            dep_outputs[dep] = self.context.stage_results[dep].outputs

                    kwargs = dict(stage.handler_kwargs)
                    kwargs["context"] = self.context
                    kwargs["inputs"] = self.context.inputs
                    kwargs["dep_outputs"] = dep_outputs

                    output = stage.handler(**kwargs)
                    if output is None:
                        output = {}

                    result.outputs = output if isinstance(output, dict) else {"result": output}
                    result.status = StageStatus.COMPLETED
                else:
                    # No handler: skip
                    result.status = StageStatus.SKIPPED

                result.end_time = time.time()
                result.runtime_seconds = result.end_time - stage_start

                self.context.stage_results[stage.name] = result

                # Log output
                self._log_stage_output(stage.name, result)

                return result

            except Exception as e:
                last_error = e
                wait_time = stage.retry_delay_seconds * (self.retry_backoff_factor ** attempt)
                self._log_stage_output(
                    stage.name,
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)

        # All attempts exhausted
        error_str = f"All {1 + stage.retry_attempts} attempts failed. Last error: {last_error}"
        return StageResult(
            stage_name=stage.name,
            status=StageStatus.FAILED,
            error=error_str,
            runtime_seconds=time.time() - start_time,
        )

    # ──────────────────────────────────────────────────────────
    # Checkpointing
    # ──────────────────────────────────────────────────────────

    def _save_checkpoint(self, pipeline_id: str) -> None:
        """Save pipeline state as checkpoint."""
        import json

        checkpoint_path = self.checkpoint_dir / f"{pipeline_id}.json"
        try:
            data = {
                "pipeline_id": pipeline_id,
                "status": self.status.value,
                "shared_data": self.context.shared_data if self.context else {},
                "stage_results": {
                    name: result.to_dict()
                    for name, result in (self.context.stage_results.items() if self.context else {})
                },
                "timestamp": time.time(),
            }
            with open(checkpoint_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save checkpoint: {e}")

    def _load_checkpoint(self, pipeline_id: str) -> bool:
        """Load pipeline state from checkpoint."""
        import json

        checkpoint_path = self.checkpoint_dir / f"{pipeline_id}.json"
        if not checkpoint_path.exists():
            return False

        try:
            with open(checkpoint_path) as f:
                data = json.load(f)

            if self.context:
                self.context.shared_data = data.get("shared_data", {})
                for name, result_data in data.get("stage_results", {}).items():
                    result = StageResult(
                        stage_name=result_data["stage_name"],
                        status=StageStatus(result_data["status"]),
                        error=result_data.get("error"),
                        runtime_seconds=result_data.get("runtime_seconds", 0.0),
                    )
                    self.context.stage_results[name] = result

            return True
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────
    # Reporting & Logging
    # ──────────────────────────────────────────────────────────

    def _log_stage_output(self, stage_name: str, message: Any) -> None:
        """Log stage output to file."""
        log_path = self.log_dir / f"{self.context.pipeline_id if self.context else 'unknown'}.log"
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a") as f:
                if isinstance(message, StageResult):
                    f.write(f"[{timestamp}] {stage_name}: {message.status.value} ({message.runtime_seconds:.2f}s)\n")
                else:
                    f.write(f"[{timestamp}] {stage_name}: {message}\n")
        except Exception:
            pass

    def get_progress(self) -> Dict:
        """Get pipeline progress information."""
        if not self.stages:
            return {"total": 0, "completed": 0, "progress": 0.0}

        total = len(self.stages)
        completed = sum(
            1 for s in (self.context.stage_results.values() if self.context else [])
            if s.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
        )
        failed = sum(
            1 for s in (self.context.stage_results.values() if self.context else [])
            if s.status == StageStatus.FAILED
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "progress": completed / total * 100 if total > 0 else 0,
            "status": self.status.value,
            "pipeline_id": self.context.pipeline_id if self.context else None,
        }

    def _get_stage_set(self, stage_name: str, reverse: bool = False) -> Set[str]:
        """Get the set of stages from/to a given stage."""
        if stage_name not in self.stages:
            return set(self.stages.keys())

        layers = self._get_execution_order()
        stage_set = set()

        for layer in layers:
            for name in layer:
                if not reverse:
                    stage_set.add(name)
                    if name == stage_name:
                        return stage_set
                else:
                    stage_set.add(name)

        if reverse:
            # Reverse mode: everything after and including
            found = False
            result = set()
            for layer in layers:
                for name in layer:
                    if name == stage_name:
                        found = True
                    if found:
                        result.add(name)
            return result

        return stage_set

    def cancel(self) -> None:
        """Request cancellation of the running pipeline."""
        self._cancel_requested = True
        self.status = PipelineStatus.CANCELLED

    def get_report(self) -> Dict:
        """Generate a full execution report."""
        if not self.context:
            return {"status": "not_started"}

        return {
            "pipeline_id": self.context.pipeline_id,
            "status": self.status.value,
            "stages": [
                {
                    "name": name,
                    "status": result.status.value,
                    "runtime_seconds": result.runtime_seconds,
                    "error": result.error,
                }
                for name, result in self.context.stage_results.items()
            ],
            "total_runtime": sum(
                r.runtime_seconds for r in self.context.stage_results.values()
            ),
            "num_stages": len(self.stages),
            "completed_stages": sum(
                1 for r in self.context.stage_results.values()
                if r.status == StageStatus.COMPLETED
            ),
            "failed_stages": sum(
                1 for r in self.context.stage_results.values()
                if r.status == StageStatus.FAILED
            ),
        }
