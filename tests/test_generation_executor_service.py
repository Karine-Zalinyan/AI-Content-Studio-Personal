"""Focused tests for the provider-neutral GenerationExecutor boundary."""

from __future__ import annotations

import pytest

from models.generation_plan import GenerationJob, GenerationPlan
from services.generation_executor_service import (
    ExecutionReport,
    ExecutionResult,
    ExecutionStatus,
    GenerationExecutor,
)


# ── helpers ────────────────────────────────────────────────────────────────────


def _job(scene_number: int, sequence: int) -> GenerationJob:
    return GenerationJob(
        job_id=f"gen-{scene_number:04d}",
        shot_id=f"shot-{scene_number}",
        scene_number=scene_number,
        sequence=sequence,
        prompt=f"prompt for scene {scene_number}",
        duration=5,
    )


def _plan(*scenes: tuple[int, int], topic: str = "Test", universe_id: str | None = "u-1") -> GenerationPlan:
    return GenerationPlan(
        project_topic=topic,
        universe_id=universe_id,
        jobs=[_job(s, q) for s, q in scenes],
    )


# ── empty plan ─────────────────────────────────────────────────────────────────


def test_empty_plan_yields_empty_report() -> None:
    plan = GenerationPlan(project_topic="Empty")
    report = GenerationExecutor().execute(plan)

    assert isinstance(report, ExecutionReport)
    assert report.results == []
    assert report.project_topic == "Empty"
    assert report.universe_id is None


# ── one result per job ─────────────────────────────────────────────────────────


def test_one_result_per_job() -> None:
    plan = _plan((1, 1), (2, 2), (3, 3))
    report = GenerationExecutor().execute(plan)

    assert len(report.results) == 3


# ── deterministic sequential ordering ─────────────────────────────────────────


def test_results_ordered_by_sequence() -> None:
    # Supply jobs out-of-order to verify the executor sorts them.
    plan = _plan((3, 3), (1, 1), (2, 2))
    report = GenerationExecutor().execute(plan)

    sequences = [r.sequence for r in report.results]
    assert sequences == [1, 2, 3]


# ── stable job identity ────────────────────────────────────────────────────────


def test_job_ids_are_stable_in_result() -> None:
    plan = _plan((1, 1), (2, 2))
    report = GenerationExecutor().execute(plan)

    assert report.results[0].job_id == "gen-0001"
    assert report.results[1].job_id == "gen-0002"
    assert report.results[0].shot_id == "shot-1"
    assert report.results[1].shot_id == "shot-2"


def test_scene_numbers_preserved() -> None:
    plan = _plan((5, 1), (7, 2))
    report = GenerationExecutor().execute(plan)

    assert [r.scene_number for r in report.results] == [5, 7]


# ── default (no-adapter) executor produces completed status ───────────────────


def test_no_adapter_all_completed() -> None:
    plan = _plan((1, 1), (2, 2))
    report = GenerationExecutor().execute(plan)

    assert all(r.status == ExecutionStatus.COMPLETED for r in report.results)


def test_no_adapter_empty_provider_response() -> None:
    plan = _plan((1, 1))
    report = GenerationExecutor().execute(plan)

    assert report.results[0].provider_response == {}
    assert report.results[0].error_message is None


# ── adapter success ────────────────────────────────────────────────────────────


def test_adapter_result_forwarded() -> None:
    def mock_adapter(job: GenerationJob) -> dict:
        return {"asset_url": f"https://cdn.example.com/{job.job_id}.mp4"}

    plan = _plan((1, 1), (2, 2))
    report = GenerationExecutor(adapter=mock_adapter).execute(plan)

    assert report.results[0].status == ExecutionStatus.COMPLETED
    assert report.results[0].provider_response == {
        "asset_url": "https://cdn.example.com/gen-0001.mp4"
    }


# ── adapter failure propagation ────────────────────────────────────────────────


def test_adapter_failure_produces_failed_status() -> None:
    def failing_adapter(job: GenerationJob) -> dict:
        raise RuntimeError("upstream timeout")

    plan = _plan((1, 1))
    report = GenerationExecutor(adapter=failing_adapter).execute(plan)

    assert report.results[0].status == ExecutionStatus.FAILED
    assert "upstream timeout" in (report.results[0].error_message or "")


def test_adapter_failure_does_not_stop_subsequent_jobs() -> None:
    calls: list[str] = []

    def flaky_adapter(job: GenerationJob) -> dict:
        calls.append(job.job_id)
        if job.sequence == 1:
            raise ValueError("flaky")
        return {}

    plan = _plan((1, 1), (2, 2), (3, 3))
    report = GenerationExecutor(adapter=flaky_adapter).execute(plan)

    assert len(report.results) == 3
    assert report.results[0].status == ExecutionStatus.FAILED
    assert report.results[1].status == ExecutionStatus.COMPLETED
    assert report.results[2].status == ExecutionStatus.COMPLETED
    assert len(calls) == 3


# ── plan is never mutated ──────────────────────────────────────────────────────


def test_executor_does_not_mutate_plan() -> None:
    plan = _plan((1, 1), (2, 2))
    snapshot = plan.model_dump(mode="json")

    GenerationExecutor().execute(plan)

    assert plan.model_dump(mode="json") == snapshot


# ── canonical IDs propagate through the report ────────────────────────────────


def test_canonical_ids_in_report() -> None:
    plan = _plan((1, 1), topic="My Project", universe_id="universe-42")
    report = GenerationExecutor().execute(plan)

    assert report.project_topic == "My Project"
    assert report.universe_id == "universe-42"


# ── aggregate helpers ─────────────────────────────────────────────────────────


def test_succeeded_and_failed_partitions() -> None:
    def partial_adapter(job: GenerationJob) -> dict:
        if job.sequence == 2:
            raise RuntimeError("boom")
        return {}

    plan = _plan((1, 1), (2, 2), (3, 3))
    report = GenerationExecutor(adapter=partial_adapter).execute(plan)

    assert len(report.succeeded) == 2
    assert len(report.failed) == 1
    assert report.failed[0].sequence == 2
