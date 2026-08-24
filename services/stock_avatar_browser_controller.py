"""Application controller for the browser-facing free stock + Avatar flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.project_history_service import ProjectHistoryService
from services.stock_avatar_web_service import StockAvatarWebService


class StockAvatarBrowserController:
    """Coordinate validation, assembly, and durable history for browser requests."""

    def __init__(
        self,
        history: ProjectHistoryService,
        assembly: StockAvatarWebService | None = None,
        output_root: str | Path | None = None,
    ) -> None:
        self.history = history
        self.assembly = assembly or StockAvatarWebService()
        self.output_root = Path(output_root).resolve() if output_root is not None else None

    def assemble(
        self,
        *,
        topic: str,
        stock_clips: list[dict[str, Any]],
        avatar_reference: str | None,
        output_path: str | Path,
    ) -> dict[str, Any]:
        requested_output = Path(output_path).resolve()
        if self.output_root is not None:
            try:
                requested_output.relative_to(self.output_root)
            except ValueError as exc:
                raise RuntimeError("Assembly output is outside the configured output root") from exc

        project, output = self.assembly.assemble_request(
            topic=topic,
            stock_clips=stock_clips,
            avatar_reference=avatar_reference,
            output_path=requested_output,
        )
        output_file = Path(output).resolve()
        if not output_file.is_file():
            raise RuntimeError("Assembly completed without producing an output file")
        if self.output_root is not None:
            try:
                stored_output_path = str(output_file.relative_to(self.output_root))
            except ValueError as exc:
                raise RuntimeError("Assembly output is outside the configured output root") from exc
        else:
            stored_output_path = str(output_file)

        project_id = self.history.create_project(topic=project.topic)
        job_id = self.history.create_job(project_id)
        metadata = dict(project.video.metadata)
        metadata["stock_clip_count"] = len(stock_clips)
        metadata["output_filename"] = output_file.name
        self.history.update_job(
            job_id,
            status="done",
            output_path=stored_output_path,
            output_metadata=metadata,
        )
        return {
            "project_id": project_id,
            "job_id": job_id,
            "status": "done",
            "output_path": stored_output_path,
            "metadata": metadata,
        }
