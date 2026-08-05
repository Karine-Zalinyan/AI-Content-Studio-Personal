"""
BaseAgent – abstract contract that every agent must implement.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from config.settings import settings


class BaseAgent(ABC):
    """
    All agents inherit from this class.

    Subclasses must implement :meth:`run` with their specific parameters.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
        self.settings = settings

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent's primary workflow."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
