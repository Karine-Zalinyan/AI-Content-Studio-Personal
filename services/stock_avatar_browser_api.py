"""Framework-neutral request adapter for the browser stock + Avatar flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


class StockAvatarBrowserRequestAdapter:
    """Validate browser payloads without coupling the UI to the assembler."""

    MAX_TOPIC_LENGTH = 500
    MAX_CLIPS = 6

    @staticmethod
    def _require_https_url(value: str, field: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"{field} must be an HTTPS URL")
        return value

    @classmethod
    def parse(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        topic = str(payload.get("topic", "")).strip()
        if not topic:
            raise ValueError("Topic cannot be empty")
        if len(topic) > cls.MAX_TOPIC_LENGTH:
            raise ValueError(f"Topic cannot exceed {cls.MAX_TOPIC_LENGTH} characters")

        raw_clips = payload.get("stock_clips", [])
        if isinstance(raw_clips, str):
            try:
                raw_clips = json.loads(raw_clips)
            except json.JSONDecodeError as exc:
                raise ValueError("stock_clips must be valid JSON") from exc
        if not isinstance(raw_clips, list):
            raise ValueError("stock_clips must be a list")
        if not raw_clips:
            raise ValueError("At least one stock clip is required")
        if len(raw_clips) > cls.MAX_CLIPS:
            raise ValueError(f"No more than {cls.MAX_CLIPS} stock clips are allowed")
        if not all(isinstance(clip, dict) for clip in raw_clips):
            raise ValueError("Each stock clip must be an object")

        clips: list[dict[str, Any]] = []
        for clip in raw_clips:
            normalized = dict(clip)
            for field in ("preview_url", "source_url"):
                value = normalized.get(field)
                if value is not None:
                    normalized[field] = cls._require_https_url(str(value).strip(), field)
            clips.append(normalized)

        avatar = payload.get("avatar_reference")
        avatar_reference = str(avatar).strip() if avatar is not None else None
        if avatar_reference:
            avatar_reference = cls._require_https_url(avatar_reference, "avatar_reference")

        output_path = str(payload.get("output_path", "")).strip()
        if not output_path:
            raise ValueError("output_path is required")

        return {
            "topic": topic,
            "stock_clips": clips,
            "avatar_reference": avatar_reference or None,
            "output_path": Path(output_path),
        }
