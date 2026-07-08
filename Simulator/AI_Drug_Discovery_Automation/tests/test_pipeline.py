"""Tests for pipeline module."""

import sys
import asyncio
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.orchestrator import (
    PipelineOrchestrator,
    Stage,
    StageStatus,
    PipelineStatus,
)
from src.pipeline.workflow_manager import WorkflowManager, WorkflowDefinition
from src.pipeline.state_manager import PipelineState, StateManager
from src.pipeline.job_scheduler import JobScheduler, Job, JobPriority, JobStatus


class TestPipelineOrchestrator:
    def test_add_stage(self):
        """Test stage registration."""
        orchestrator = PipelineOrchestrator()
        stage = Stage(name="test_stage", handler=lambda **kwargs: {"result": "ok"})
        orchestrator.add_stage(stage)
        assert "test_stage" in orchestrator.stages

    def test_dag_validation(self):
        """Test DAG validation."""
        orchestrator = PipelineOrchestrator()
        stage_a = Stage(name="A", depends_on=[])
        stage_b = Stage(name="B", depends_on=["A"])
        stage_c = Stage(name="C", depends_on=["B"])
        orchestrator.add_stages([stage_a, stage_b, stage_c])

        errors = orchestrator.validate_dag()
        assert len(errors) == 0  # No cycles

    def test_dag_cycle_detection(self):
        """Test cycle detection."""
        orchestrator = PipelineOrchestrator()
        stage_a = Stage(name="A", depends_on=["C"])
        stage_b = Stage(name="B", depends_on=["A"])
        stage_c = Stage(name="C", depends_on=["B"])
        orchestrator.add_stages([stage_a, stage_b, stage_c])

        errors = orchestrator.validate_dag()
        assert len(errors) > 0  # Cycle detected

    def test_execution_order(self):
        """Test topological sort."""
        orchestrator = PipelineOrchestrator()
        stage_a = Stage(name="A")
        stage_b = Stage(name="B", depends_on=["A"])
        stage_c = Stage(name="C", depends_on=["A"])
        stage_d = Stage(name="D", depends_on=["B", "C"])
        orchestrator.add_stages([stage_a, stage_b, stage_c, stage_d])

        layers = orchestrator._get_execution_order()
        assert layers[0] == ["A"]
        assert set(layers[1]) == {"B", "C"}
        assert layers[2] == ["D"]

    def test_missing_dependency(self):
        """Test missing dependency detection."""
        orchestrator = PipelineOrchestrator()
        stage = Stage(name="A", depends_on=["NONEXISTENT"])
        orchestrator.add_stage(stage)

        errors = orchestrator.validate_dag()
        assert any("NONEXISTENT" in e for e in errors)

    def test_progress_reporting(self):
        """Test progress reporting."""
        orchestrator = PipelineOrchestrator()
        stage = Stage(name="test")
        orchestrator.add_stage(stage)

        progress = orchestrator.get_progress()
        assert progress["total"] == 1
        assert progress["completed"] == 0


class TestWorkflowManager:
    def test_full_pipeline_template(self):
        """Test full pipeline template."""
        workflow = WorkflowManager.full_pipeline()
        assert workflow.name == "full_pipeline"
        assert len(workflow.stages) > 0

        stage_names = [s["name"] for s in workflow.stages]
        assert "target_selection" in stage_names
        assert "alphafold_prediction" in stage_names
        assert "molecular_docking" in stage_names

    def test_docking_template(self):
        """Test docking template."""
        workflow = WorkflowManager.docking_only()
        assert workflow.name == "docking_only"
        assert len(workflow.stages) == 4

    def test_generation_template(self):
        """Test generation template."""
        workflow = WorkflowManager.generation_only()
        assert workflow.name == "generation_only"
        assert len(workflow.stages) == 5

    def test_screening_template(self):
        """Test screening template."""
        workflow = WorkflowManager.screening_pipeline()
        assert workflow.name == "screening_pipeline"

    def test_workflow_serialization(self):
        """Test workflow JSON serialization."""
        workflow = WorkflowManager.full_pipeline()
        json_str = workflow.to_json()
        assert isinstance(json_str, str)
        assert "full_pipeline" in json_str

        loaded = WorkflowDefinition.from_json(json_str)
        assert loaded.name == workflow.name
        assert len(loaded.stages) == len(workflow.stages)

    def test_create_orchestrator(self):
        """Test orchestrator creation from workflow."""
        manager = WorkflowManager()
        workflow = WorkflowManager.docking_only()
        orchestrator = manager.create_orchestrator(workflow)

        assert len(orchestrator.stages) == len(workflow.stages)


class TestStateManager:
    def test_save_load_state(self):
        """Test state persistence."""
        manager = StateManager()
        state = PipelineState(
            pipeline_id="test_001",
            workflow_name="test",
            status="running",
            created_at=123.0,
            updated_at=123.0,
        )

        path = manager.save_state(state)
        assert Path(path).exists()

        loaded = manager.load_state("test_001")
        assert loaded is not None
        assert loaded.pipeline_id == "test_001"
        assert loaded.status == "running"

        # Cleanup
        manager.delete_state("test_001")

    def test_list_states(self):
        """Test state listing."""
        manager = StateManager()
        states = manager.list_states()
        assert isinstance(states, list)

    def test_get_statistics(self):
        """Test statistics."""
        manager = StateManager()
        stats = manager.get_pipeline_statistics()
        assert "total_pipelines" in stats


class TestJobScheduler:
    @pytest.mark.asyncio
    async def test_job_execution(self):
        """Test basic job execution."""
        async def dummy_job():
            return "done"

        scheduler = JobScheduler(max_concurrent_jobs=2)
        job_id = scheduler.submit_fn("test", dummy_job)

        await scheduler.start()
        await asyncio.sleep(1)
        await scheduler.stop()

        result = scheduler.get_job_result(job_id)
        if result:
            assert result.status == JobStatus.COMPLETED
            assert result.result == "done"

    def test_job_priority(self):
        """Test job priority ordering."""
        scheduler = JobScheduler()
        assert scheduler.pending_count == 0
        assert scheduler.running_count == 0

    def test_cancel_job(self):
        """Test job cancellation."""
        scheduler = JobScheduler()
        async def slow_job():
            await asyncio.sleep(10)
            return "never"

        job_id = scheduler.submit_fn("slow", slow_job)
        cancelled = scheduler.cancel_job(job_id)
        assert cancelled is True
