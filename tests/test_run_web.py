from __future__ import annotations

import run_web
from services import stock_avatar_ui_server


def test_stock_search_submit_is_bridged_without_native_navigation(monkeypatch) -> None:
    original = stock_avatar_ui_server.HTML
    html = '<form id="stock-search"><button id="stock-submit" class="secondary" type="submit">Search</button></form></body>'
    monkeypatch.setattr(stock_avatar_ui_server, "HTML", html)

    run_web._patch_stock_search_submit()

    assert 'id="stock-submit" class="secondary" type="button"' in stock_avatar_ui_server.HTML
    assert "button.addEventListener('click', runSearch)" in stock_avatar_ui_server.HTML
    assert "searchStock()" in stock_avatar_ui_server.HTML
    assert "requestSubmit()" not in stock_avatar_ui_server.HTML

    monkeypatch.setattr(stock_avatar_ui_server, "HTML", original)
