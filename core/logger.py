"""
Logging configuration for AI Content Studio Personal.
"""

import logging
import sys
from pathlib import Path

from config.settings import settings


def _build_formatter() -> logging.Formatter:
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    return logging.Formatter(fmt=fmt, datefmt=datefmt)


def setup_logging() -> None:
    """Configure root logger with console (and optionally file) handlers."""
    level = logging.DEBUG if settings.debug else logging.INFO
    formatter = _build_formatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    handlers: list[logging.Handler] = [console_handler]

    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.  Call after :func:`setup_logging`."""
    return logging.getLogger(name)
