import inspect

from services.stock_avatar_ui_server import StockAvatarStudioHandler


def test_stock_avatar_handler_distinguishes_validation_and_runtime_errors() -> None:
    source = inspect.getsource(StockAvatarStudioHandler.do_POST)
    assert "HTTPStatus.BAD_REQUEST" in source
    assert "HTTPStatus.INTERNAL_SERVER_ERROR" in source
    assert "except (ValueError, json.JSONDecodeError)" in source
    assert "except (RuntimeError, OSError)" in source
