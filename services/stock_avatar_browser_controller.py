"""Application controller for the browser-facing free stock + Avatar flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.project_history_service import ProjectHistoryService
from services.stock_avatar_web_service import StockAvatarWebService


class StockAvatarBrowserController:
    """Coordinate validation, assembly, and durable history for browser requests.

    This controller deliberately stays above the existing assembly/domain service
    and below the HTTP UI. It does not introduce a second generation pipeline.
    """

    def __init__(
        self,
        history: ProjectHistoryService,
        assembly: StockAvatarWebService | None = None,
    ) -> None:
        self.history = history
        self.assembly = assembly or StockAvatarWebService()

    def assemble(
        self,
        *,
        topic: str,
        stock_clips: list[dict[str, Any]],
        avatar_reference: str | None,
        output_path: str | Path,
    ) -> dict[str, Any]:
        project, output = self.assembly.assemble_request(
            topic=topic,
            stock_clips=stock_clips,
            avatar_reference=avatar_reference,
            output_path=output_path,
        )
        project_id = self.history.create_project(topic=project.topic)
        job_id = self.history.create_job(project_id)
        relative_output = Path(output).name
        metadata = dict(project.video.metadata)
        metadata["stock_clip_count"] = len(stock_clips)
        self.history.update_job(
            job_id,
            status="done",
            output_path=relative_output,
            output_metadata=metadata,
        )
        return {
            "project_id": project_id,
            "job_id": job_id,
            "status": "done",
            "output_path": relative_output,
            "metadata": metadata,
        }
