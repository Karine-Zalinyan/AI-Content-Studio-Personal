"""Browser-facing projection for persisted project/generation history.

This keeps presentation concerns out of ProjectHistoryService while preserving
AI Universe IDs as canonical continuity metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.project_history_service import ProjectHistoryService


class ProjectHistoryWebService:
    """Build safe, UI-ready recent-project records from durable history."""

    def __init__(self, history: ProjectHistoryService, output_dir: Path | str) -> None:
        self.history = history
        self.output_dir = Path(output_dir).resolve()

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in self.history.list_recent(limit):
            record = {
                "job_id": item["id"],
                "project_id": item["project_id"],
                "topic": item["topic"],
                "status": item["status"],
                "updated_at": item["updated_at"],
                "universe_id": item.get("universe_id"),
                "avatar_id": item.get("avatar_id"),
                "location_id": item.get("location_id"),
                "error_message": item.get("error_message", ""),
                "video_url": self.video_url(item.get("output_path")),
            }
            records.append(record)
        return records

    def video_url(self, output_path: str | None) -> str | None:
        if not output_path:
            return None
        candidate = Path(output_path)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.output_dir / candidate).resolve()
        try:
            relative = resolved.relative_to(self.output_dir)
        except ValueError:
            return None
        return "/output/" + relative.as_posix()
