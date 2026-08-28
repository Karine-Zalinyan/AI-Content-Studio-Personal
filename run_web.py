"""Deployment entry point for the Social Content Studio browser MVP."""

from __future__ import annotations

import os

from services import stock_avatar_ui_server
from services.stock_avatar_ui_server import serve_stock_avatar


def _port() -> int:
    raw = os.getenv("PORT", "8787")
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    return port


def _patch_stock_search_submit() -> None:
    """Prevent native form navigation and reuse the existing async search handler.

    The deployed browser symptom is a page jump to the top when the stock-search
    button is clicked. Keeping the button as a non-submit control removes the
    browser's native navigation path; requestSubmit() still routes through the
    existing stock form listener, which calls preventDefault() and performs the
    fetch to /api/stock-videos.
    """
    button_marker = 'id="stock-submit" class="secondary" type="submit"'
    button_replacement = 'id="stock-submit" class="secondary" type="button"'
    if button_marker in stock_avatar_ui_server.HTML:
        stock_avatar_ui_server.HTML = stock_avatar_ui_server.HTML.replace(
            button_marker,
            button_replacement,
            1,
        )

    bridge = """
<script>
(() => {
  const stockButton = document.getElementById('stock-submit');
  const stockForm = document.getElementById('stock-search');
  if (!stockButton || !stockForm) return;
  stockButton.addEventListener('click', () => stockForm.requestSubmit());
})();
</script>
"""
    if "stockForm.requestSubmit()" not in stock_avatar_ui_server.HTML:
        stock_avatar_ui_server.HTML = stock_avatar_ui_server.HTML.replace(
            "</body>",
            bridge + "</body>",
            1,
        )


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    _patch_stock_search_submit()
    serve_stock_avatar(host=host, port=_port())


if __name__ == "__main__":
    main()
