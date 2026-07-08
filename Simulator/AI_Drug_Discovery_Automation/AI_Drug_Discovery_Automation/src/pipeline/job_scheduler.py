"""
Job Scheduler
==============
병렬 작업 스케줄링 및 실행 관리.
비동기 작업 큐, 우선순위 기반 스케줄링, 리소스 관리.
"""

import asyncio
import time
import uuid
import heapq
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Coroutine
from dataclasses import dataclass, field

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Enums & Data Structures
# ──────────────────────────────────────────────────────────


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass(order=True)
class ScheduledJob:
    """A job scheduled for execution with priority."""
    priority: int
    scheduled_at: float
    job_id: str = field(compare=False)
    name: str = field(compare=False)
    coroutine_fn: Optional[Callable] = field(compare=False, default=None)
    kwargs: Dict[str, Any] = field(compare=False, default_factory=dict)
    timeout: int = field(compare=False, default=3600)


@dataclass
class JobResult:
    """Result of a job execution."""
    job_id: str
    name: str
    status: JobStatus
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    runtime_seconds: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "status": self.status.value,
            "error": self.error,
            "runtime_seconds": self.runtime_seconds,
        }


class Job:
    """
    A single executable job wrapping a coroutine with metadata.
    """

    def __init__(
        self,
        name: str,
        fn: Callable,
        kwargs: Optional[Dict] = None,
        priority: JobPriority = JobPriority.NORMAL,
        timeout: int = 3600,
        tags: Optional[List[str]] = None,
    ):
        self.job_id = f"job_{uuid.uuid4().hex[:12]}"
        self.name = name
        self.fn = fn
        self.kwargs = kwargs or {}
        self.priority = priority
        self.timeout = timeout
        self.tags = tags or []
        self.result: Optional[JobResult] = None

        self._created_at = time.time()
        self._status = JobStatus.PENDING

    @property
    def status(self) -> JobStatus:
        return self._status

    async def execute(self) -> JobResult:
        """Execute the job."""
        start_time = time.time()
        self._status = JobStatus.RUNNING

        try:
            if asyncio.iscoroutinefunction(self.fn):
                result = await asyncio.wait_for(
                    self.fn(**self.kwargs),
                    timeout=self.timeout,
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(self.fn, **self.kwargs),
                    timeout=self.timeout,
                )

            self._status = JobStatus.COMPLETED
            self.result = JobResult(
                job_id=self.job_id,
                name=self.name,
                status=JobStatus.COMPLETED,
                result=result,
                start_time=start_time,
                end_time=time.time(),
                runtime_seconds=time.time() - start_time,
            )

        except asyncio.TimeoutError:
            self._status = JobStatus.FAILED
            self.result = JobResult(
                job_id=self.job_id,
                name=self.name,
                status=JobStatus.FAILED,
                error=f"Job timed out after {self.timeout}s",
                start_time=start_time,
                end_time=time.time(),
                runtime_seconds=time.time() - start_time,
            )

        except Exception as e:
            self._status = JobStatus.FAILED
            self.result = JobResult(
                job_id=self.job_id,
                name=self.name,
                status=JobStatus.FAILED,
                error=f"{type(e).__name__}: {str(e)}",
                start_time=start_time,
                end_time=time.time(),
                runtime_seconds=time.time() - start_time,
            )

        return self.result

    def cancel(self) -> None:
        """Mark the job as cancelled."""
        self._status = JobStatus.CANCELLED
        self.result = JobResult(
            job_id=self.job_id,
            name=self.name,
            status=JobStatus.CANCELLED,
        )

    def __repr__(self) -> str:
        return f"Job(name={self.name}, status={self._status.value})"


# ──────────────────────────────────────────────────────────
# Job Scheduler
# ──────────────────────────────────────────────────────────


class JobScheduler:
    """
    Async job scheduler with priority queue.

    Features:
        - Priority-based scheduling
        - Concurrent execution with max_workers limit
        - Job timeout handling
        - Progress tracking and cancellation
        - Job dependency management
    """

    def __init__(self, max_concurrent_jobs: int = 4):
        self.max_concurrent_jobs = max_concurrent_jobs
        self._queue: List[ScheduledJob] = []
        self._running: Dict[str, Job] = {}
        self._completed: Dict[str, JobResult] = {}
        self._failed: Dict[str, JobResult] = {}
        self._job_registry: Dict[str, Job] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._active = False
        self._worker_task: Optional[asyncio.Task] = None

    # ──────────────────────────────────────────────────────────
    # Job Submission
    # ──────────────────────────────────────────────────────────

    def submit(self, job: Job) -> str:
        """
        Submit a job for execution.

        Args:
            job: Job to execute

        Returns:
            Job ID
        """
        self._job_registry[job.job_id] = job
        scheduled = ScheduledJob(
            priority=job.priority.value,
            scheduled_at=time.time(),
            job_id=job.job_id,
            name=job.name,
            timeout=job.timeout,
        )
        heapq.heappush(self._queue, scheduled)
        return job.job_id

    def submit_fn(
        self,
        name: str,
        fn: Callable,
        kwargs: Optional[Dict] = None,
        priority: JobPriority = JobPriority.NORMAL,
        timeout: int = 3600,
    ) -> str:
        """
        Convenience method to submit a function as a job.

        Args:
            name: Job name
            fn: Function to execute
            kwargs: Keyword arguments
            priority: Job priority
            timeout: Timeout in seconds

        Returns:
            Job ID
        """
        job = Job(name=name, fn=fn, kwargs=kwargs, priority=priority, timeout=timeout)
        return self.submit(job)

    def submit_batch(self, jobs: List[Job]) -> List[str]:
        """Submit multiple jobs at once."""
        return [self.submit(j) for j in jobs]

    # ──────────────────────────────────────────────────────────
    # Execution
    # ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the scheduler worker."""
        if self._active:
            return
        self._active = True
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        """Stop the scheduler worker."""
        self._active = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def _worker_loop(self) -> None:
        """Main worker loop: pull jobs from queue and execute."""
        while self._active:
            if not self._queue or len(self._running) >= self.max_concurrent_jobs:
                await asyncio.sleep(0.1)
                continue

            scheduled = heapq.heappop(self._queue)
            job = self._job_registry.get(scheduled.job_id)

            if job is None or job.status == JobStatus.CANCELLED:
                continue

            self._running[job.job_id] = job
            asyncio.create_task(self._execute_job(job))

    async def _execute_job(self, job: Job) -> None:
        """Execute a single job with semaphore control."""
        async with self._semaphore:
            result = await job.execute()

        self._running.pop(job.job_id, None)

        if result.status == JobStatus.COMPLETED:
            self._completed[job.job_id] = result
        elif result.status == JobStatus.FAILED:
            self._failed[job.job_id] = result

    # ──────────────────────────────────────────────────────────
    # Synchronous convenience
    # ──────────────────────────────────────────────────────────

    def run_until_complete(self, jobs: Optional[List[Job]] = None) -> Dict[str, JobResult]:
        """
        Synchronously run jobs and wait for completion.

        Args:
            jobs: Optional list of jobs to submit first

        Returns:
            Dict of job_id → JobResult
        """
        if jobs:
            self.submit_batch(jobs)

        return asyncio.run(self._run_async())

    async def _run_async(self) -> Dict[str, JobResult]:
        """Internal async runner."""
        await self.start()

        # Wait until queue is empty and nothing is running
        while self._queue or self._running:
            await asyncio.sleep(0.5)

        await self.stop()
        return {**self._completed, **self._failed}

    # ──────────────────────────────────────────────────────────
    # Job Control
    # ──────────────────────────────────────────────────────────

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        # Try to remove from queue
        self._queue[:] = [j for j in self._queue if j.job_id != job_id]
        heapq.heapify(self._queue)

        # Cancel running job
        job = self._job_registry.get(job_id)
        if job and job.status == JobStatus.RUNNING:
            job.cancel()
            self._running.pop(job_id, None)
            self._completed[job_id] = job.result
            return True

        if job and job.status == JobStatus.PENDING:
            job.cancel()
            self._completed[job_id] = job.result
            return True

        return False

    def cancel_all(self) -> int:
        """Cancel all pending and running jobs."""
        count = len(self._queue) + len(self._running)

        for scheduled in self._queue:
            job = self._job_registry.get(scheduled.job_id)
            if job:
                job.cancel()

        for job_id, job in list(self._running.items()):
            job.cancel()

        self._queue.clear()
        self._running.clear()
        return count

    def retry_failed(self, max_retries: int = 1) -> List[str]:
        """
        Resubmit all failed jobs.

        Args:
            max_retries: Maximum retry count per job

        Returns:
            List of new job IDs
        """
        new_ids = []
        for job_id, result in list(self._failed.items()):
            original = self._job_registry.get(job_id)
            if original:
                new_job = Job(
                    name=f"{original.name}_retry",
                    fn=original.fn,
                    kwargs=original.kwargs,
                    timeout=original.timeout,
                )
                new_ids.append(self.submit(new_job))

        self._failed.clear()
        return new_ids

    # ──────────────────────────────────────────────────────────
    # Status & Reporting
    # ──────────────────────────────────────────────────────────

    @property
    def pending_count(self) -> int:
        return len(self._queue)

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def failed_count(self) -> int:
        return len(self._failed)

    def get_status(self) -> Dict:
        """Get full scheduler status."""
        return {
            "active": self._active,
            "queue_size": len(self._queue),
            "running": self.running_count,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "max_concurrent": self.max_concurrent_jobs,
            "running_jobs": [
                {"id": j.job_id, "name": j.name, "elapsed": time.time() - j._created_at}
                for j in self._running.values()
            ],
            "recent_completed": [
                r.to_dict() for r in list(self._completed.values())[-10:]
            ],
            "recent_failed": [
                r.to_dict() for r in list(self._failed.values())[-10:]
            ],
        }

    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Get result for a specific job."""
        if job_id in self._completed:
            return self._completed[job_id]
        if job_id in self._failed:
            return self._failed[job_id]
        return None

    def wait_for_completion(self, job_id: str, timeout: Optional[int] = None) -> Optional[JobResult]:
        """
        Wait for a specific job to complete.

        Args:
            job_id: Job ID to wait for
            timeout: Maximum wait time in seconds

        Returns:
            JobResult or None if timeout
        """
        start = time.time()
        while job_id not in self._completed and job_id not in self._failed:
            if timeout and (time.time() - start) > timeout:
                return None
            time.sleep(0.5)
        return self.get_job_result(job_id)

    def clear_completed(self) -> int:
        """Clear completed job results."""
        count = len(self._completed)
        self._completed.clear()
        return count

    def clear_all(self) -> None:
        """Clear all jobs and results."""
        self.cancel_all()
        self._completed.clear()
        self._failed.clear()
        self._job_registry.clear()
