"""
AI Content Studio Personal – entry point.

Usage:
    python main.py
"""

from config.settings import settings
from core.logger import setup_logging


def main() -> None:
    # 1. Ensure runtime directories exist
    settings.ensure_dirs()

    # 2. Boot the logger (must happen before any other import that logs)
    setup_logging()

    # 3. Late import so logger is ready when modules are initialised
    from core.app import App

    # 4. Run
    App().run()


if __name__ == "__main__":
    main()
