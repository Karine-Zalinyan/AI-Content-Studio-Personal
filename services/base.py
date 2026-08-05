"""
BaseService – abstract contract that every service must implement.

Services wrap a single external dependency (an API, a file store, etc.).
They are stateless by convention and injected into agents.
"""

from __future__ import annotations

import logging
from abc import ABC

from config.settings import settings


class BaseService(ABC):
    """Shared foundation for all service wrappers."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
        self.settings = settings

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
