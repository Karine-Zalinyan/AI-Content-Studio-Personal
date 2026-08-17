"""Deployment entry point for the Social Content Studio browser MVP."""

from __future__ import annotations

import os

from web_ui import serve


def _port() -> int:
    raw = os.getenv("PORT", "8787")
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    return port


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    serve(host=host, port=_port())


if __name__ == "__main__":
    main()
