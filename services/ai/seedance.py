"""
SeedanceProvider

Wraps the Seedance AI video-generation API.
Best suited for: Pixar-style, animation, stylized, fantasy content.
"""

from __future__ import annotations

from models.project import GeneratedAsset, GenerationJob
from services.ai.base import BaseAIProvider


class SeedanceProvider(BaseAIProvider):
    """Seedance AI provider – animation, stylized, and fantasy content."""

    def generate(self, job: GenerationJob) -> GeneratedAsset:
        """
        Call the Seedance API to generate a video clip for *job*.

        Raises:
            NotImplementedError: Seedance API integration is not yet wired up.
        """
        raise NotImplementedError(
            f"SeedanceProvider is not yet integrated. "
            f"Implement API calls here for scene {job.scene_number}."
        )
