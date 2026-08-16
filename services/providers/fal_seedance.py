"""Small fal gateway adapter for Seedance 2.0 text-to-video generation."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import httpx

from models.generation_plan import GenerationJob


FAL_SEEDANCE_ENDPOINT = "https://fal.run/bytedance/seedance-2.0/text-to-video"


class FalSeedanceAdapter:
    """Callable provider adapter compatible with GenerationExecutor.

    The API key is read from ``FAL_KEY`` and is never stored in project data.
    ``http_client`` is injectable so tests can use an in-memory MockTransport.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
        endpoint: str = FAL_SEEDANCE_ENDPOINT,
    ) -> None:
        self._api_key = api_key or os.getenv("FAL_KEY", "").strip()
        self._client = http_client
        self._endpoint = endpoint

    def __call__(self, job: GenerationJob) -> dict[str, Any]:
        if not self._api_key:
            raise RuntimeError("FAL_KEY is required for Seedance generation.")

        prompt = (job.video_prompt or job.prompt).strip()
        if not prompt:
            raise ValueError(f"Generation job '{job.job_id}' has no video prompt.")

        if job.negative_constraints:
            prompt = f"{prompt}\nConstraints: {', '.join(job.negative_constraints)}"

        duration = min(max(job.duration or 5, 4), 15)
        payload = {
            "prompt": prompt,
            "resolution": "720p",
            "duration": str(duration),
            "aspect_ratio": job.aspect_ratio or "9:16",
            "generate_audio": False,
            "bitrate_mode": "standard",
        }

        client = self._client or httpx.Client(timeout=300.0)
        owns_client = self._client is None
        try:
            response = client.post(
                self._endpoint,
                headers={"Authorization": f"Key {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Seedance provider request failed: {exc}") from exc
        finally:
            if owns_client:
                client.close()

        video = data.get("video") or {}
        video_url = video.get("url") if isinstance(video, dict) else None
        if not video_url:
            raise RuntimeError("Seedance provider returned no video URL.")

        request_id = data.get("request_id") or data.get("requestId") or response.headers.get("x-fal-request-id", "")
        return {
            "provider": "fal",
            "model": "bytedance/seedance-2.0/text-to-video",
            "request_id": request_id,
            "asset_url": video_url,
            "content_type": video.get("content_type", "video/mp4") if isinstance(video, dict) else "video/mp4",
            "file_name": video.get("file_name", "video.mp4") if isinstance(video, dict) else "video.mp4",
            "resolution": payload["resolution"],
            "duration": duration,
            "aspect_ratio": payload["aspect_ratio"],
        }
