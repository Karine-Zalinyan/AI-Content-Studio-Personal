"""
GenerationExecutorAgent

Executes the generation plan built by GenerationPlannerAgent.
Reads project.generation_jobs, dispatches each PENDING job to the
correct AI provider, and writes results back to project.assets and
project.generation_jobs.

Does not make planning decisions – only executes the ready-made plan.
"""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import NamedTuple

from agents.base import BaseAgent
from models.project import GeneratedAsset, GenerationJob, GenerationLog, Project
from services.ai.base import BaseAIProvider
from services.ai.higgsfield import HiggsfieldProvider
from services.ai.kling import KlingProvider
from services.ai.runway import RunwayProvider
from services.ai.seedance import SeedanceProvider

_PROVIDER_MAP: dict[str, type[BaseAIProvider]] = {
    "seedance": SeedanceProvider,
    "kling": KlingProvider,
    "runway": RunwayProvider,
    "higgsfield": HiggsfieldProvider,
}


class _JobResult(NamedTuple):
    asset: GeneratedAsset | None
    log: GenerationLog


class GenerationExecutorAgent(BaseAgent):
    """Execute pending generation jobs and populate project.assets."""

    def run(self, project: Project) -> Project:
        pending = [job for job in project.generation_jobs if job.status == "PENDING"]
        if not pending:
            self.logger.info("No PENDING generation jobs – nothing to execute.")
            return project

        groups = self._group_by_parallel_group(pending)
        for group_id in sorted(groups.keys()):
            self.logger.info(
                "Executing parallel group %d (%d job(s)).", group_id, len(groups[group_id])
            )
            results = self._execute_group(groups[group_id])
            for result in results:
                project.generation_logs.append(result.log)
                if result.asset is not None:
                    project.assets.ai_videos.append(result.asset)

        return project

    def _execute_group(self, jobs: list[GenerationJob]) -> list[_JobResult]:
        results: list[_JobResult] = []
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            future_to_job: dict[Future[_JobResult], GenerationJob] = {
                pool.submit(self._execute_job, job): job for job in jobs
            }
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # noqa: BLE001 – safety net; _execute_job never raises
                    self.logger.error(
                        "Scene %d raised an unexpected exception: %s", job.scene_number, exc
                    )
        return results

    def _execute_job(self, job: GenerationJob) -> _JobResult:
        job.status = "RUNNING"
        started_at = datetime.now(tz=timezone.utc)
        started_ts = time.monotonic()

        try:
            provider = self._build_provider(job)
            asset = provider.generate(job)
            elapsed = time.monotonic() - started_ts
            finished_at = datetime.now(tz=timezone.utc)

            asset.generation_time = round(elapsed, 3)
            job.status = "DONE"

            self.logger.info(
                "Scene %d done via %s in %.1fs (cost $%.4f).",
                job.scene_number,
                job.provider,
                elapsed,
                asset.cost,
            )
            return _JobResult(
                asset=asset,
                log=self._build_log(job, started_at, finished_at, elapsed, asset.cost, ""),
            )

        except Exception as exc:  # noqa: BLE001
            elapsed = time.monotonic() - started_ts
            finished_at = datetime.now(tz=timezone.utc)
            error_message = str(exc)

            self.logger.warning(
                "Scene %d failed via %s after %.1fs: %s",
                job.scene_number,
                job.provider,
                elapsed,
                error_message,
            )

            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = "PENDING"
                self.logger.info(
                    "Scene %d queued for retry (%d/%d).",
                    job.scene_number,
                    job.retry_count,
                    job.max_retries,
                )
            else:
                job.status = "FAILED"

            return _JobResult(
                asset=None,
                log=self._build_log(job, started_at, finished_at, elapsed, 0.0, error_message),
            )

    def _build_provider(self, job: GenerationJob) -> BaseAIProvider:
        provider_cls = _PROVIDER_MAP.get(job.provider)
        if provider_cls is None:
            raise ValueError(f"Unknown provider '{job.provider}' for scene {job.scene_number}.")
        return provider_cls()

    @staticmethod
    def _group_by_parallel_group(jobs: list[GenerationJob]) -> dict[int, list[GenerationJob]]:
        groups: dict[int, list[GenerationJob]] = {}
        for job in jobs:
            groups.setdefault(job.parallel_group, []).append(job)
        return groups

    @staticmethod
    def _build_log(
        job: GenerationJob,
        started_at: datetime,
        finished_at: datetime,
        generation_time: float,
        cost: float,
        error_message: str,
    ) -> GenerationLog:
        return GenerationLog(
            scene_number=job.scene_number,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            provider=job.provider,
            generation_time=round(generation_time, 3),
            cost=cost,
            error_message=error_message,
        )
