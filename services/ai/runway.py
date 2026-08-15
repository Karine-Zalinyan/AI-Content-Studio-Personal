"""
RunwayProvider

Wraps the Runway AI video-generation API.
Best suited for: cinematic realism, live action, human subjects, documentary style.
"""

from __future__ import annotations

from models.project import GeneratedAsset, GenerationJob
from services.ai.base import BaseAIProvider


class RunwayProvider(BaseAIProvider):
    """Runway AI provider – cinematic realism and live-action content."""

    def generate(self, job: GenerationJob) -> GeneratedAsset:
        """
        Call the Runway API to generate a video clip for *job*.

        Raises:
            NotImplementedError: Runway API integration is not yet wired up.
        """
        raise NotImplementedError(
            f"RunwayProvider is not yet integrated. "
            f"Implement API calls here for scene {job.scene_number}."
        )
