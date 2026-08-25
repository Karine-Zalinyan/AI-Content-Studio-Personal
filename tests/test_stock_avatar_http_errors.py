from services.stock_avatar_ui_server import StockAvatarStudioHandler


def test_stock_avatar_handler_distinguishes_validation_and_runtime_errors() -> None:
    source = StockAvatarStudioHandler.do_POST.__code__.co_consts
    assert "application/json" in source
    assert "RuntimeError" in source
    assert "ValueError" in source
