"""
Route registry – maps menu choices to agent/service handlers.

Every new feature registers itself here; the App loop just calls
``router.dispatch(choice)``.
"""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Type alias for a handler: a zero-argument callable that performs the action
Handler = Callable[[], None]


class Router:
    """Lightweight command router."""

    def __init__(self) -> None:
        self._routes: dict[str, Handler] = {}

    # ── Registration ─────────────────────────────────────────────────────────

    def register(self, key: str, handler: Handler) -> None:
        """Register *handler* under menu *key* (e.g. ``"1"``)."""
        if key in self._routes:
            logger.warning("Route '%s' is being overwritten.", key)
        self._routes[key] = handler
        logger.debug("Route registered: key='%s' handler='%s'", key, handler.__qualname__)

    # ── Dispatch ─────────────────────────────────────────────────────────────

    def dispatch(self, key: str) -> bool:
        """
        Call the handler associated with *key*.

        Returns ``True`` if a handler was found and executed,
        ``False`` otherwise.
        """
        handler = self._routes.get(key)
        if handler is None:
            return False
        try:
            handler()
        except Exception:
            logger.exception("Unhandled error in handler for key='%s'.", key)
        return True

    # ── Introspection ─────────────────────────────────────────────────────────

    def registered_keys(self) -> list[str]:
        return list(self._routes.keys())
