"""Application-layer helpers for creating Universe-aware content projects."""

from __future__ import annotations

from agents.universe_context_agent import UniverseContextAgent
from models.project import Project
from models.universe import Universe


class ContentProjectService:
    """Create Projects while preserving canonical Universe character identity."""

    def __init__(self, universe_context_agent: UniverseContextAgent | None = None) -> None:
        self._universe_context_agent = universe_context_agent or UniverseContextAgent()

    def create_from_avatar(
        self,
        topic: str,
        universe: Universe,
        avatar_id: str,
        *,
        location_ids: list[str] | None = None,
    ) -> Project:
        """Create a Project linked to an existing canonical Avatar/Character.

        The Universe is read-only: ``UniverseContextAgent`` resolves an explicit
        snapshot into the Project's ``UniverseReference`` without copying the
        character into a competing project-level model.
        """
        avatar = universe.get_character(avatar_id)
        if avatar is None:
            raise ValueError(
                f"Avatar '{avatar_id}' does not exist in Universe '{universe.id}'."
            )

        project = Project(topic=topic)
        return self._universe_context_agent.run(
            project,
            universe,
            character_ids=[avatar.id],
            location_ids=location_ids,
        )
