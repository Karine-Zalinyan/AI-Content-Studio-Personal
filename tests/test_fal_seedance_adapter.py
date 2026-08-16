"""Focused tests for the fal Seedance provider adapter."""

from __future__ import annotations

import json

import httpx
import pytest

from models.generation_plan import GenerationJob
from services.providers.fal_seedance import FalSeedanceAdapter


def _job(**overrides) -> GenerationJob:
    values = {
        "job_id": "gen-1",
        "shot_id": "shot-1",
        "scene_number": 1,
        "sequence": 1,
        "prompt": "A child helps a parent.",
        "video_prompt": "A child gently helps a parent carry boxes.",
        "duration": 5,
        "aspect_ratio": "9:16",
    }
    values.update(overrides)
    return GenerationJob(**values)


def test_missing_api_key_is_rejected() -> None:
    adapter = FalSeedanceAdapter(api_key="")

    with pytest.raises(RuntimeError, match="FAL_KEY is required"):
        adapter(_job())


def test_success_maps_request_and_normalizes_response() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["json"] = json.loads(request.read().decode())
        return httpx.Response(
            200,
            json={
                "video": {
                    "url": "https://example.com/generated.mp4",
                    "content_type": "video/mp4",
                    "file_name": "generated.mp4",
                },
                "seed": 42,
            },
            headers={"x-fal-request-id": "req-123"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = FalSeedanceAdapter(api_key="test-key", http_client=client)(_job(duration=20))

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/bytedance/seedance-2.0/text-to-video")
    assert captured["headers"]["authorization"] == "Key test-key"
    assert captured["json"]["duration"] == "15"
    assert captured["json"]["aspect_ratio"] == "9:16"
    assert captured["json"]["resolution"] == "720p"
    assert result["provider"] == "fal"
    assert result["request_id"] == "req-123"
    assert result["asset_url"] == "https://example.com/generated.mp4"
    assert result["resolution"] == "720x1280"


def test_negative_constraints_are_appended_without_mutating_job() -> None:
    job = _job(negative_constraints=["no text", "no watermark"])
    before = job.model_dump(mode="json")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.read().decode()
        return httpx.Response(200, json={"video": {"url": "https://example.com/video.mp4"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    FalSeedanceAdapter(api_key="test-key", http_client=client)(job)

    assert "Constraints: no text, no watermark" in captured["json"]
    assert job.model_dump(mode="json") == before


def test_provider_http_error_is_normalized() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"detail": "rate limited"})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="Seedance provider request failed"):
        FalSeedanceAdapter(api_key="test-key", http_client=client)(_job())


def test_missing_video_url_is_rejected() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"seed": 42})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="no video URL"):
        FalSeedanceAdapter(api_key="test-key", http_client=client)(_job())
