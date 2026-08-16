"""Provider-neutral GenerationExecutor application-layer boundary.

Accepts a GenerationPlan and produces one traceable ExecutionResult per job.
Provider-specific I/O is injected via an optional adapter callable, keeping
this service side-effect free by default.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Optional

from pydantic import Field

from models.base import AppBaseModel
from models.generation_plan import GenerationJob, GenerationPlan


class ExecutionStatus(str, Enum):
    """Lifecycle status for one generation job execution."""

    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionResult(AppBaseModel):
    """Traceable result for a single GenerationJob execution."""

    job_id: str
    shot_id: str
    scene_number: int
    sequence: int
    status: ExecutionStatus
    provider_response: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ExecutionReport(AppBaseModel):
    """Aggregate report for one GenerationPlan execution run."""

    project_topic: str
    universe_id: Optional[str] = None
    results: list[ExecutionResult] = Field(default_factory=list)

    @property
    def succeeded(self) -> list[ExecutionResult]:
        return [r for r in self.results if r.status == ExecutionStatus.COMPLETED]

    @property
    def failed(self) -> list[ExecutionResult]:
        return [r for r in self.results if r.status == ExecutionStatus.FAILED]


# A provider adapter receives a GenerationJob and returns a dict of provider
# response data on success, or raises an exception on failure.
ProviderAdapter = Callable[[GenerationJob], dict[str, Any]]


class GenerationExecutor:
    """Execute a GenerationPlan sequentially without mutating the input plan.

    Args:
        adapter: Optional callable that performs the actual media-generation
                 call for each job.  When omitted the executor produces a
                 ``completed`` result with an empty provider_response, which
                 is useful for testing and dry-run scenarios.
    """

    def __init__(self, adapter: Optional[ProviderAdapter] = None) -> None:
        self._adapter = adapter

    def execute(self, plan: GenerationPlan) -> ExecutionReport:
        """Run every job in deterministic sequence order and return a report.

        The input *plan* is never mutated.
        """
        ordered = sorted(plan.jobs, key=lambda j: j.sequence)
        results = [self._execute_job(job) for job in ordered]
        return ExecutionReport(
            project_topic=plan.project_topic,
            universe_id=plan.universe_id,
            results=results,
        )

    def _execute_job(self, job: GenerationJob) -> ExecutionResult:
        if self._adapter is None:
            return ExecutionResult(
                job_id=job.job_id,
                shot_id=job.shot_id,
                scene_number=job.scene_number,
                sequence=job.sequence,
                status=ExecutionStatus.COMPLETED,
            )
        try:
            provider_response = self._adapter(job)
            return ExecutionResult(
                job_id=job.job_id,
                shot_id=job.shot_id,
                scene_number=job.scene_number,
                sequence=job.sequence,
                status=ExecutionStatus.COMPLETED,
                provider_response=provider_response,
            )
        except Exception as exc:  # noqa: BLE001
            return ExecutionResult(
                job_id=job.job_id,
                shot_id=job.shot_id,
                scene_number=job.scene_number,
                sequence=job.sequence,
                status=ExecutionStatus.FAILED,
                error_message=str(exc),
            )
