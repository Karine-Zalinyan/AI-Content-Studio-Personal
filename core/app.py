"""
Application orchestrator.

``App`` wires together the router, agents, and services, then drives the
interactive menu loop.  Business logic lives in agents/services – never here.
"""

from __future__ import annotations

import json
import logging

from config.settings import settings
from core.orchestrator import PipelineOrchestrator
from core.router import Router
from models.project import Project

logger = logging.getLogger(__name__)

# ── Menu definition ───────────────────────────────────────────────────────────
# Each entry: (key, label, handler_name_on_App)
# Add new items here when new agents are ready.
MENU_ITEMS: list[tuple[str, str]] = [
    ("1", "Create Viral Video"),
]


class App:
    """Top-level application class."""

    def __init__(self) -> None:
        self.router = Router()
        self._running = False
        self._register_routes()

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    def _register_routes(self) -> None:
        """Wire menu keys to handler methods."""
        self.router.register("1", self._handle_create_viral_video)
        # Future agents: self.router.register("2", self._handle_next_feature)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _handle_create_viral_video(self) -> None:
        """Collect a topic, generate an idea, create a director plan, and print both."""
        topic = input("\nEnter topic: ").strip()
        if not topic:
            print("\nTopic cannot be empty.\n")
            return

        project = Project(topic=topic)

        try:
            project = PipelineOrchestrator().run(project)
        except ValueError as exc:
            if "OPENROUTER_API_KEY" in str(exc):
                print("\nPlease configure your OpenRouter API key in the .env file.\n")
                return
            logger.exception("Pipeline execution failed.")
            print(f"\nError: {exc}\n")
            return
        except Exception as exc:
            logger.exception("Pipeline execution failed.")
            print(f"\nError: {exc}\n")
            return

        # Print results
        print("\n" + "=" * 25)
        print("IDEA")
        print("=" * 25)
        print()
        print(json.dumps(project.idea.model_dump(), indent=2, ensure_ascii=False))
        print()

        print("=" * 25)
        print("DIRECTOR PLAN")
        print("=" * 25)
        print()
        print(json.dumps(project.director.model_dump(), indent=2, ensure_ascii=False))
        print()

    # ── UI helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _print_menu() -> None:
        print()
        print("=" * 34)
        print(settings.app_name.upper())
        print("=" * 34)
        print()
        for key, label in MENU_ITEMS:
            print(f"{key}. {label}")
        print()
        print("0. Exit")
        print()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the interactive CLI loop."""
        logger.info("Application started (env=%s, debug=%s).", settings.app_env, settings.debug)
        self._running = True

        while self._running:
            self._print_menu()

            try:
                choice = input("\n  Enter your choice: ").strip()
            except (KeyboardInterrupt, EOFError):
                choice = "0"
                print()

            if choice == "0":
                self._running = False
                print("\n  Goodbye!\n")
                logger.info("Application exited by user.")
                break

            if not self.router.dispatch(choice):
                print(f"\n  Invalid option '{choice}'. Please try again.\n")
                logger.debug("Unknown menu choice: '%s'.", choice)
