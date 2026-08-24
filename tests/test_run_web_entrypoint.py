import run_web


def test_web_entrypoint_uses_stock_avatar_server() -> None:
    assert run_web.serve_stock_avatar.__module__ == "services.stock_avatar_ui_server"
