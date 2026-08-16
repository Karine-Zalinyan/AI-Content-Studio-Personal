"""Focused tests for deterministic generated-video export."""

from __future__ import annotations

from pathlib import Path

import pytest

from models.project import GeneratedAsset
import services.generated_video_export_service as export_module
from services.generated_video_export_service import GeneratedVideoExportService
from services.generation_executor_service import ExecutionReport, ExecutionResult, ExecutionStatus


def _result(
    *,
    job_id: str,
    scene_number: int,
    sequence: int,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
) -> ExecutionResult:
    return ExecutionResult(
        job_id=job_id,
        shot_id=f"shot-{scene_number}",
        scene_number=scene_number,
        sequence=sequence,
        status=status,
    )


def _asset(
    tmp_path: Path,
    *,
    name: str,
    scene_number: int,
    job_id: str,
    sequence: int,
    resolution: str = "1080x1920",
    aspect_ratio: str | None = "9:16",
) -> GeneratedAsset:
    path = tmp_path / name
    path.write_bytes(name.encode("utf-8"))
    metadata = {
        "job_id": job_id,
        "sequence": sequence,
    }
    if aspect_ratio is not None:
        metadata["aspect_ratio"] = aspect_ratio
    return GeneratedAsset(
        scene_number=scene_number,
        provider="fal",
        file_path=str(path),
        duration=5.0,
        resolution=resolution,
        metadata=metadata,
    )


def test_exports_clips_in_execution_order_to_deterministic_path(tmp_path) -> None:
    report = ExecutionReport(
        project_topic="My Test Project",
        results=[
            _result(job_id="gen-2", scene_number=2, sequence=2),
            _result(job_id="gen-1", scene_number=1, sequence=1),
            _result(job_id="gen-3", scene_number=3, sequence=3),
        ],
    )
    assets = [
        _asset(tmp_path, name="scene-3.mp4", scene_number=3, job_id="gen-3", sequence=3),
        _asset(tmp_path, name="scene-1.mp4", scene_number=1, job_id="gen-1", sequence=1),
        _asset(tmp_path, name="scene-2.mp4", scene_number=2, job_id="gen-2", sequence=2),
    ]
    seen: list[str] = []

    def assembler(clips: list[GeneratedAsset], destination: Path) -> None:
        seen.extend(Path(asset.file_path).name for asset in clips)
        destination.write_bytes(b"joined-video")

    video = GeneratedVideoExportService(tmp_path / "exports", assembler=assembler).export(report, assets)

    assert seen == ["scene-1.mp4", "scene-2.mp4", "scene-3.mp4"]
    assert video.file_path == str((tmp_path / "exports" / "My_Test_Project_9x16.mp4").resolve())
    assert Path(video.file_path).read_bytes() == b"joined-video"
    assert video.resolution == "1080x1920"
    assert video.metadata["scene_numbers"] == [1, 2, 3]
    assert video.metadata["aspect_ratio"] == "9:16"
    assert video.format == "mp4"


def test_empty_report_is_rejected(tmp_path) -> None:
    service = GeneratedVideoExportService(tmp_path, assembler=lambda clips, destination: destination.write_bytes(b""))

    with pytest.raises(ValueError, match="no generated clips"):
        service.export(ExecutionReport(project_topic="Empty"), [])


def test_missing_asset_fails_clearly(tmp_path) -> None:
    report = ExecutionReport(project_topic="Missing", results=[_result(job_id="gen-1", scene_number=1, sequence=1)])

    with pytest.raises(RuntimeError, match="Missing persisted generated asset"):
        GeneratedVideoExportService(tmp_path).export(report, [])


def test_failed_generation_result_prevents_partial_export(tmp_path) -> None:
    report = ExecutionReport(
        project_topic="Partial",
        results=[
            _result(job_id="gen-1", scene_number=1, sequence=1),
            _result(job_id="gen-2", scene_number=2, sequence=2, status=ExecutionStatus.FAILED),
        ],
    )
    assets = [_asset(tmp_path, name="scene-1.mp4", scene_number=1, job_id="gen-1", sequence=1)]
    calls = 0

    def assembler(clips: list[GeneratedAsset], destination: Path) -> None:
        nonlocal calls
        calls += 1
        destination.write_bytes(b"should-not-run")

    with pytest.raises(RuntimeError, match=r"non-completed generation jobs: gen-2 \(failed\)"):
        GeneratedVideoExportService(tmp_path / "exports", assembler=assembler).export(report, assets)

    assert calls == 0
    assert not (tmp_path / "exports" / "Partial_9x16.mp4").exists()


def test_non_9_16_asset_is_rejected(tmp_path) -> None:
    report = ExecutionReport(project_topic="Wrong Ratio", results=[_result(job_id="gen-1", scene_number=1, sequence=1)])
    asset = _asset(
        tmp_path,
        name="scene-1.mp4",
        scene_number=1,
        job_id="gen-1",
        sequence=1,
        resolution="1920x1080",
        aspect_ratio="16:9",
    )

    with pytest.raises(RuntimeError, match="not 9:16-compatible"):
        GeneratedVideoExportService(tmp_path).export(report, [asset])


def test_resolution_fallback_rejects_non_9_16_asset(tmp_path) -> None:
    report = ExecutionReport(project_topic="Wrong Resolution", results=[_result(job_id="gen-1", scene_number=1, sequence=1)])
    asset = _asset(
        tmp_path,
        name="scene-1.mp4",
        scene_number=1,
        job_id="gen-1",
        sequence=1,
        resolution="1920x1080",
        aspect_ratio=None,
    )

    with pytest.raises(RuntimeError, match="not 9:16-compatible"):
        GeneratedVideoExportService(tmp_path).export(report, [asset])


def test_export_does_not_mutate_report_or_assets(tmp_path) -> None:
    report = ExecutionReport(
        project_topic="Immutable",
        results=[
            _result(job_id="gen-2", scene_number=2, sequence=2),
            _result(job_id="gen-1", scene_number=1, sequence=1),
        ],
    )
    assets = [
        _asset(tmp_path, name="scene-2.mp4", scene_number=2, job_id="gen-2", sequence=2),
        _asset(tmp_path, name="scene-1.mp4", scene_number=1, job_id="gen-1", sequence=1),
    ]
    before_report = report.model_dump(mode="json")
    before_assets = [asset.model_dump(mode="json") for asset in assets]

    GeneratedVideoExportService(
        tmp_path / "exports",
        assembler=lambda clips, destination: destination.write_bytes(b"joined-video"),
    ).export(report, assets)

    assert report.model_dump(mode="json") == before_report
    assert [asset.model_dump(mode="json") for asset in assets] == before_assets


def test_unreadable_asset_path_is_rejected(tmp_path) -> None:
    report = ExecutionReport(project_topic="Unreadable", results=[_result(job_id="gen-1", scene_number=1, sequence=1)])
    bad_path = tmp_path / "not-a-file.mp4"
    bad_path.mkdir()
    asset = GeneratedAsset(
        scene_number=1,
        provider="fal",
        file_path=str(bad_path),
        duration=5.0,
        resolution="1080x1920",
        metadata={"job_id": "gen-1", "sequence": 1, "aspect_ratio": "9:16"},
    )

    with pytest.raises(RuntimeError, match="missing or unreadable"):
        GeneratedVideoExportService(tmp_path).export(report, [asset])


def test_default_ffmpeg_concat_reencodes_to_real_output_resolution(tmp_path, monkeypatch) -> None:
    report = ExecutionReport(
        project_topic="Concat",
        results=[
            _result(job_id="gen-1", scene_number=1, sequence=1),
            _result(job_id="gen-2", scene_number=2, sequence=2),
        ],
    )
    assets = [
        _asset(tmp_path, name="scene-1.mp4", scene_number=1, job_id="gen-1", sequence=1, resolution="1080x1920"),
        _asset(tmp_path, name="scene-2.mp4", scene_number=2, job_id="gen-2", sequence=2, resolution="720x1280"),
    ]
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool, capture_output: bool, text: bool):
        del check, capture_output, text
        commands.append(command)
        Path(command[-1]).write_bytes(b"joined-video")

        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        return Result()

    monkeypatch.setattr(export_module.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(export_module.subprocess, "run", fake_run)

    video = GeneratedVideoExportService(tmp_path / "exports").export(report, assets)

    assert video.resolution == "720x1280"
    assert len(commands) == 1
    command = commands[0]
    assert "-filter_complex" in command
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "scale=720:1280" in filter_graph
    assert "concat=n=2:v=1:a=0[vout]" in filter_graph
    assert "copy" not in command
    assert command[command.index("-c:v") + 1] == "libx264"
