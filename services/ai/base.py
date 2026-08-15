"""
BaseAIProvider – abstract contract every AI generation provider must implement.
"""

from __future__ import annotations

from abc import abstractmethod

from models.project import GeneratedAsset, GenerationJob
from services.base import BaseService


class BaseAIProvider(BaseService):
    """
    Abstract base for AI video-generation provider wrappers.

    Subclasses implement :meth:`generate` with provider-specific API calls.
    The method must be synchronous; parallel execution is handled by the
    executor agent, not the provider.
    """

    @abstractmethod
    def generate(self, job: GenerationJob) -> GeneratedAsset:
        """
        Execute generation for *job* and return the resulting asset.

        Raises:
            RuntimeError: if the provider API returns an error.
            NotImplementedError: if the provider is not yet integrated.
        """
