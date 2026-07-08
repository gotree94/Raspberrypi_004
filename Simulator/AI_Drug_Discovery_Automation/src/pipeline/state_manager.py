"""
Pipeline State Manager
=======================
파이프라인 상태 영속성, 체크포인트 관리, 실행 기록 추적.
"""

import json
import time
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────


@dataclass
class PipelineState:
    """Serializable pipeline state."""
    pipeline_id: str
    workflow_name: str
    status: str = "created"
    current_stage: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    stage_states: Dict[str, str] = field(default_factory=dict)
    stage_outputs: Dict[str, Dict] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    completed_at: Optional[float] = None
    version: int = 1

    def update(self, **kwargs) -> None:
        """Update state fields and increment version."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = time.time()
        self.version += 1

    def to_dict(self) -> Dict:
        return {
            "pipeline_id": self.pipeline_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "current_stage": self.current_stage,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "stage_states": self.stage_states,
            "stage_outputs": self.stage_outputs,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PipelineState":
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "PipelineState":
        return cls.from_dict(json.loads(json_str))


@dataclass
class ExecutionRecord:
    """Execution history record."""
    stage_name: str
    pipeline_id: str
    status: str
    start_time: float
    end_time: Optional[float] = None
    runtime_seconds: float = 0.0
    error: Optional[str] = None
    artifacts: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────
# State Manager
# ──────────────────────────────────────────────────────────


class StateManager:
    """
    Pipeline state persistence manager.

    Handles:
        - Save/load pipeline state
        - Execution history tracking
        - State listing and search
        - Automatic cleanup of old states
    """

    def __init__(self, config: Optional[Any] = None):
        cfg = config or get_config()
        pipe_cfg = cfg.pipeline
        self.state_dir = Path(pipe_cfg.checkpoint_dir) / "states"
        self.history_dir = Path(pipe_cfg.log_dir) / "history"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: PipelineState) -> str:
        """
        Save pipeline state to disk.

        Args:
            state: Pipeline state to save

        Returns:
            Path to saved state file
        """
        filepath = self.state_dir / f"{state.pipeline_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(state.to_json())
        return str(filepath)

    def load_state(self, pipeline_id: str) -> Optional[PipelineState]:
        """
        Load pipeline state from disk.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            PipelineState or None if not found
        """
        filepath = self.state_dir / f"{pipeline_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, encoding="utf-8") as f:
                return PipelineState.from_json(f.read())
        except (json.JSONDecodeError, KeyError):
            return None

    def delete_state(self, pipeline_id: str) -> bool:
        """Delete a saved pipeline state."""
        filepath = self.state_dir / f"{pipeline_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def list_states(
        self,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        List saved pipeline states.

        Args:
            status_filter: Optional status filter
            limit: Maximum number of states to return

        Returns:
            List of state summaries
        """
        states = []
        for filepath in sorted(self.state_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                if status_filter and data.get("status") != status_filter:
                    continue
                states.append({
                    "pipeline_id": data.get("pipeline_id"),
                    "workflow_name": data.get("workflow_name"),
                    "status": data.get("status"),
                    "current_stage": data.get("current_stage"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "version": data.get("version"),
                })
                if len(states) >= limit:
                    break
            except (json.JSONDecodeError, IOError):
                continue

        return states

    def save_execution_record(self, record: ExecutionRecord) -> str:
        """
        Save an execution record to history.

        Args:
            record: Execution record

        Returns:
            Path to saved record file
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{record.pipeline_id}_{record.stage_name}_{timestamp}.json"
        filepath = self.history_dir / filename

        data = {
            "stage_name": record.stage_name,
            "pipeline_id": record.pipeline_id,
            "status": record.status,
            "start_time": record.start_time,
            "end_time": record.end_time,
            "runtime_seconds": record.runtime_seconds,
            "error": record.error,
            "artifacts": record.artifacts,
            "metrics": record.metrics,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return str(filepath)

    def get_execution_history(
        self,
        pipeline_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Retrieve execution history.

        Args:
            pipeline_id: Optional filter by pipeline ID
            stage_name: Optional filter by stage name
            limit: Maximum records to return

        Returns:
            List of execution records
        """
        records = []
        for filepath in sorted(self.history_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                if pipeline_id and data.get("pipeline_id") != pipeline_id:
                    continue
                if stage_name and data.get("stage_name") != stage_name:
                    continue
                records.append(data)
                if len(records) >= limit:
                    break
            except (json.JSONDecodeError, IOError):
                continue

        return records

    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get aggregate pipeline execution statistics."""
        states = self.list_states(limit=1000)
        records = self.get_execution_history(limit=1000)

        if not states:
            return {"total_pipelines": 0}

        completed = sum(1 for s in states if s["status"] == "completed")
        failed = sum(1 for s in states if s["status"] == "failed")
        running = sum(1 for s in states if s["status"] == "running")

        total_runtime = sum(r.get("runtime_seconds", 0) for r in records)

        return {
            "total_pipelines": len(states),
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": completed / max(1, len(states)) * 100,
            "total_executions": len(records),
            "total_runtime_seconds": total_runtime,
        }


# ──────────────────────────────────────────────────────────
# Checkpoint Manager
# ──────────────────────────────────────────────────────────


class CheckpointManager:
    """
    Stage-level checkpoint manager for partial pipeline resume.

    Supports:
        - Save/load stage outputs as checkpoint
        - Automatic checkpoint naming
        - Multiple checkpoint formats (JSON, pickle)
    """

    def __init__(self, config: Optional[Any] = None):
        cfg = config or get_config()
        pipe_cfg = cfg.pipeline
        self.checkpoint_dir = Path(pipe_cfg.checkpoint_dir) / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        pipeline_id: str,
        stage_name: str,
        data: Any,
        fmt: str = "json",
    ) -> str:
        """
        Save a stage checkpoint.

        Args:
            pipeline_id: Pipeline ID
            stage_name: Stage name
            data: Data to checkpoint
            fmt: Format ("json" or "pickle")

        Returns:
            Path to checkpoint file
        """
        filename = f"{pipeline_id}_{stage_name}.{fmt}"
        filepath = self.checkpoint_dir / filename

        if fmt == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        else:
            with open(filepath, "wb") as f:
                pickle.dump(data, f)

        return str(filepath)

    def load_checkpoint(
        self,
        pipeline_id: str,
        stage_name: str,
        fmt: str = "json",
    ) -> Optional[Any]:
        """
        Load a stage checkpoint.

        Args:
            pipeline_id: Pipeline ID
            stage_name: Stage name
            fmt: Format ("json" or "pickle")

        Returns:
            Checkpoint data or None
        """
        filepath = self.checkpoint_dir / f"{pipeline_id}_{stage_name}.{fmt}"
        if not filepath.exists():
            return None

        try:
            if fmt == "json":
                with open(filepath, encoding="utf-8") as f:
                    return json.load(f)
            else:
                with open(filepath, "rb") as f:
                    return pickle.load(f)
        except Exception:
            return None

    def has_checkpoint(self, pipeline_id: str, stage_name: str) -> bool:
        """Check if a checkpoint exists."""
        for fmt in ("json", "pickle"):
            if (self.checkpoint_dir / f"{pipeline_id}_{stage_name}.{fmt}").exists():
                return True
        return False

    def list_checkpoints(self, pipeline_id: Optional[str] = None) -> List[str]:
        """
        List all checkpoints.

        Args:
            pipeline_id: Optional filter

        Returns:
            List of checkpoint file names
        """
        checkpoints = []
        for filepath in self.checkpoint_dir.glob("*"):
            if pipeline_id and not filepath.stem.startswith(pipeline_id):
                continue
            checkpoints.append(filepath.name)
        return sorted(checkpoints)

    def delete_checkpoints(self, pipeline_id: str) -> int:
        """Delete all checkpoints for a pipeline."""
        count = 0
        for filepath in self.checkpoint_dir.glob(f"{pipeline_id}_*"):
            filepath.unlink()
            count += 1
        return count

    def clear_all(self) -> int:
        """Clear all checkpoints."""
        count = 0
        for filepath in self.checkpoint_dir.glob("*"):
            filepath.unlink()
            count += 1
        return count

    def get_checkpoint_size(self, pipeline_id: Optional[str] = None) -> int:
        """Get total size of checkpoint files in bytes."""
        total = 0
        for filepath in self.checkpoint_dir.glob("*"):
            if pipeline_id and not filepath.stem.startswith(pipeline_id):
                continue
            total += filepath.stat().st_size
        return total
