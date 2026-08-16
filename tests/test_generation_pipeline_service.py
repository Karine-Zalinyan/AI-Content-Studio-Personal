"""Focused tests for the end-to-end generation/export orchestration boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from models.generation_plan import GenerationJob, GenerationPlan
from models.project import GeneratedAsset, VideoOutput
from services.generation_executor_service import ExecutionReport, ExecutionResult, ExecutionStatus, GenerationExecutor
from services.generation_pipeline_service import GenerationPipelineService


def _plan(*jobs: GenerationJob) -> GenerationPlan:
    return GenerationPlan(project_topic="MVP Test", universe_id="universe-1", jobs=list(jobs))


def _job(scene: int, sequence: int) -> GenerationJob:
    return GenerationJob(
        job_id=f"gen-{scene}",
        shot_id=f"shot-{scene}",
        scene_number=scene,
        sequence=sequence,
        prompt=f"Scene {scene}",
        video_prompt=f"Video scene {scene}",
        duration=5,
        aspect_ratio="9:16",
    )


def _asset(tmp_path: Path, scene: int, job_id: str) -> GeneratedAsset:
    path = tmp_path / f"scene-{scene}.mp4"
    path.write_bytes(b"fake-mp4")
    return GeneratedAsset(
        scene_number=scene,
        provider="fal",
        file_path=str(path),
        duration=5,
        resolution="720x1280",
        metadata={"job_id": job_id, "aspect_ratio": "9:16"},
    )


class FakePersistence:
    def __init__(self, assets: list[GeneratedAsset]) -> None:
        self.assets = assets
        self.reports: list[ExecutionReport] = []

    def persist(self, report: ExecutionReport) -> list[GeneratedAsset]:
        self.reports.append(report)
        return self.assets


class FakeExporter:
    def __init__(self) -> None:
        self.calls: list[tuple[ExecutionReport, tuple[GeneratedAsset, ...]]] = []

    def export(self, report: ExecutionReport, assets: tuple[GeneratedAsset, ...]) -> VideoOutput:
        self.calls.append((report, assets))
        return VideoOutput(
            file_path="output/MVP_Test_9x16.mp4",
            duration=10,
            resolution="720x1280",
            format="mp4",
            metadata={"aspect_ratio": "9:16", "scene_numbers": [1, 2]},
        )


def test_success_runs_execute_persist_and_export_in_order(tmp_path: Path) -> None:
    jobs = [_job(2, 2), _job(1, 1)]
    persistence = FakePersistence([_asset(tmp_path, 1, "gen-1"), _asset(tmp_path, 2, "gen-2")])
    exporter = FakeExporter()

    pipeline = GenerationPipelineService(
        adapter=lambda job: {"asset_url": f"https://example.com/{job.job_id}.mp4"},
        persistence=persistence,
        exporter=exporter,
    )

    result = pipeline.run(_plan(*jobs))

    assert [item.sequence for item in result.report.results] == [1, 2]
    assert result.report.universe_id == "universe-1"
    assert len(result.assets) == 2
    assert result.video.file_path.endswith("MVP_Test_9x16.mp4")
    assert len(persistence.reports) == 1
    assert len(exporter.calls) == 1
    assert exporter.calls[0][0] is result.report
    assert exporter.calls[0][1] == result.assets


def test_failed_generation_stops_before_persistence_and_export() -> None:
    persistence = FakePersistence([])
    exporter = FakeExporter()

    def failing_adapter(job: GenerationJob) -> dict:
        if job.scene_number == 2:
            raise RuntimeError("provider timeout")
        return {"asset_url": f"https://example.com/{job.job_id}.mp4"}

    pipeline = GenerationPipelineService(
        adapter=failing_adapter,
        persistence=persistence,
        exporter=exporter,
    )

    with pytest.raises(RuntimeError, match="provider timeout"):
        pipeline.run(_plan(_job(1, 1), _job(2, 2)))

    assert persistence.reports == []
    assert exporter.calls == []


def test_empty_plan_stops_before_export() -> None:
    persistence = FakePersistence([])
    exporter = FakeExporter()
    pipeline = GenerationPipelineService(
        adapter=lambda job: {},
        persistence=persistence,
        exporter=exporter,
    )

    with pytest.raises(ValueError, match="empty GenerationPlan"):
        pipeline.run(_plan())

    assert persistence.reports == []
    assert exporter.calls == []


def test_pipeline_preserves_executor_report_contract() -> None:
    executor = GenerationExecutor(adapter=lambda job: {"asset_url": "https://example.com/video.mp4"})
    persistence = FakePersistence([])
    exporter = FakeExporter()

    report = ExecutionReport(
        project_topic="MVP Test",
        universe_id="universe-42",
        results=[
            ExecutionResult(
                job_id="gen-1",
                shot_id="shot-1",
                scene_number=1,
                sequence=1,
                status=ExecutionStatus.COMPLETED,
                provider_response={"asset_url": "https://example.com/video.mp4"},
            )
        ],
    )

    class FixedExecutor:
        def execute(self, plan: GenerationPlan) -> ExecutionReport:
            return report

    pipeline = GenerationPipelineService(
        executor=FixedExecutor(),
        persistence=persistence,
        exporter=exporter,
    )
    pipeline.run(_plan(_job(1, 1)))

    assert persistence.reports[0].universe_id == "universe-42"
    assert persistence.reports[0].results[0].job_id == "gen-1"
