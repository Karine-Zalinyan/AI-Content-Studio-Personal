"""
KlingProvider

Wraps the Kling AI video-generation API.
Best suited for: fast motion, transformation, active action content.
"""

from __future__ import annotations

from models.project import GeneratedAsset, GenerationJob
from services.ai.base import BaseAIProvider


class KlingProvider(BaseAIProvider):
    """Kling AI provider – fast motion, transformation, and action content."""

    def generate(self, job: GenerationJob) -> GeneratedAsset:
        """
        Call the Kling API to generate a video clip for *job*.

        Raises:
            NotImplementedError: Kling API integration is not yet wired up.
        """
        raise NotImplementedError(
            f"KlingProvider is not yet integrated. "
            f"Implement API calls here for scene {job.scene_number}."
        )
