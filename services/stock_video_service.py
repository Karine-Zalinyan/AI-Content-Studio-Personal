"""Server-side stock-video search backed by Pexels."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from config.settings import settings


class StockVideoSearchService:
    """Search free stock videos without exposing provider credentials."""

    search_url = "https://api.pexels.com/videos/search"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = settings.pexels_api_key if api_key is None else api_key
        self._client = client
        self._timeout = timeout

    def search(
        self,
        query: str,
        *,
        per_page: int = 6,
        orientation: str = "portrait",
    ) -> list[dict[str, Any]]:
        text = query.strip()
        if not text:
            return []
        if not self._api_key:
            raise RuntimeError("Pexels API key is not configured")

        payload = self._request(
            params={
                "query": text,
                "per_page": per_page,
                "orientation": orientation,
            }
        )
        videos = payload.get("videos", [])
        if not isinstance(videos, list):
            return []
        return [item for video in videos if (item := self._normalize(video)) is not None]

    def _request(self, *, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": self._api_key}
        if self._client is not None:
            response = self._client.get(self.search_url, params=params, headers=headers)
        else:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(self.search_url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _normalize(self, video: Any) -> dict[str, Any] | None:
        if not isinstance(video, dict):
            return None

        width = self._as_int(video.get("width"))
        height = self._as_int(video.get("height"))
        source_url = self._safe_https_url(video.get("url"))
        thumbnail_url = self._safe_https_url(video.get("image"))
        preview_url = self._pick_preview_url(video.get("video_files"))

        return {
            "id": str(video.get("id", "")),
            "duration_seconds": self._as_int(video.get("duration")),
            "width": width,
            "height": height,
            "orientation": self._orientation(width, height),
            "thumbnail_url": thumbnail_url,
            "source_url": source_url,
            "preview_url": preview_url,
        }

    def _pick_preview_url(self, files: Any) -> str | None:
        if not isinstance(files, list):
            return None
        candidates: list[tuple[int, str]] = []
        for item in files:
            if not isinstance(item, dict):
                continue
            link = self._safe_https_url(item.get("link"))
            if not link:
                continue
            width = self._as_int(item.get("width")) or 0
            height = self._as_int(item.get("height")) or 0
            candidates.append((width * height, link))
        if not candidates:
            return None
        candidates.sort(key=lambda value: value[0] or 1, reverse=True)
        return candidates[0][1]

    def _safe_https_url(self, value: Any) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            return None
        return value

    def _orientation(self, width: int | None, height: int | None) -> str | None:
        if width is None or height is None:
            return None
        if height > width:
            return "portrait"
        if width > height:
            return "landscape"
        return "square"

    def _as_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
