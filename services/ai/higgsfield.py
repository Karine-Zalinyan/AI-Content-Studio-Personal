"""
HiggsfieldProvider

Wraps the Higgsfield AI video-generation API.
Best suited for: drone shots, FPV, orbit, complex camera movement.
"""

from __future__ import annotations

from models.project import GeneratedAsset, GenerationJob
from services.ai.base import BaseAIProvider


class HiggsfieldProvider(BaseAIProvider):
    """Higgsfield AI provider – drone, FPV, and complex camera movement content."""

    def generate(self, job: GenerationJob) -> GeneratedAsset:
        """
        Call the Higgsfield API to generate a video clip for *job*.

        Raises:
            NotImplementedError: Higgsfield API integration is not yet wired up.
        """
        raise NotImplementedError(
            f"HiggsfieldProvider is not yet integrated. "
            f"Implement API calls here for scene {job.scene_number}."
        )
