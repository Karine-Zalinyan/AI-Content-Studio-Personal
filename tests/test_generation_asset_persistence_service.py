"""Focused tests for generated video asset persistence."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from models.project import GeneratedAsset
from services.generation_asset_persistence_service import GenerationAssetPersistenceService
from services.generation_executor_service import ExecutionReport, ExecutionResult, ExecutionStatus


def _report(*results: ExecutionResult) -> ExecutionReport:
    return ExecutionReport(project_topic="Test", results=list(results))


def _result(
    *,
    job_id: str = "gen-1",
    scene_number: int = 1,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
    response: dict | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        job_id=job_id,
        shot_id=f"shot-{scene_number}",
        scene_number=scene_number,
        sequence=scene_number,
        status=status,
        provider_response=response
        or {
            "provider": "fal",
            "asset_url": "https://cdn.example.com/video.mp4",
            "request_id": "req-1",
            "duration": 5,
            "resolution": "720p",
            "aspect_ratio": "9:16",
        },
    )


def test_successful_result_is_downloaded_and_normalized(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://cdn.example.com/video.mp4"
        return httpx.Response(200, content=b"fake-mp4")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assets = GenerationAssetPersistenceService(tmp_path, http_client=client).persist(_report(_result()))

    assert len(assets) == 1
    assert isinstance(assets[0], GeneratedAsset)
    assert assets[0].provider == "fal"
    assert assets[0].duration == 5
    assert assets[0].resolution == "720p"
    assert assets[0].metadata["request_id"] == "req-1"
    assert assets[0].metadata["aspect_ratio"] == "9:16"
    assert (tmp_path / "scene_0001_gen-1.mp4").read_bytes() == b"fake-mp4"


def test_failed_results_are_skipped(tmp_path) -> None:
    assets = GenerationAssetPersistenceService(tmp_path).persist(
        _report(_result(status=ExecutionStatus.FAILED, response={"error": "timeout"}))
    )

    assert assets == []
    assert list(tmp_path.iterdir()) == []


def test_filename_is_safe_and_deterministic(tmp_path) -> None:
    result = _result(job_id="../../unsafe id")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"video")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assets = GenerationAssetPersistenceService(tmp_path, http_client=client).persist(_report(result))

    path = assets[0].file_path
    assert Path(path).parent == tmp_path.resolve()
    assert Path(path).name == "scene_0001_.._.._unsafe_id.mp4"


def test_provider_download_error_is_normalized(tmp_path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="Generated asset download failed"):
        GenerationAssetPersistenceService(tmp_path, http_client=client).persist(_report(_result()))

    assert list(tmp_path.iterdir()) == []
