"""Browser-safe application service for free stock + Avatar assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from models.project import Project
from services.stock_avatar_assembly_service import StockAvatarAssemblyService


class StockAvatarWebService:
    """Validate browser input and delegate free video assembly to the domain service."""

    MAX_CLIPS = 6
    MAX_TOPIC_LENGTH = 500

    def __init__(self, assembler: StockAvatarAssemblyService | None = None) -> None:
        self.assembler = assembler or StockAvatarAssemblyService()

    def assemble_request(
        self,
        *,
        topic: str,
        stock_clips: list[dict[str, Any]],
        avatar_reference: str | None,
        output_path: str | Path,
    ) -> tuple[Project, Path]:
        normalized_topic = topic.strip()
        if not normalized_topic:
            raise ValueError("Topic cannot be empty")
        if len(normalized_topic) > self.MAX_TOPIC_LENGTH:
            raise ValueError("Topic is too long")
        if not isinstance(stock_clips, list) or not stock_clips:
            raise ValueError("At least one stock clip is required")
        if len(stock_clips) > self.MAX_CLIPS:
            raise ValueError("A maximum of 6 stock clips is supported")
        if avatar_reference is not None and not isinstance(avatar_reference, str):
            raise ValueError("Avatar reference must be a URL")

        project = Project(topic=normalized_topic)
        output = self.assembler.assemble(
            project,
            stock_clips,
            avatar_reference=avatar_reference,
            output_path=output_path,
        )
        return project, output
