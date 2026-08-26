from services.stock_avatar_ui_server import HTML


def test_stock_avatar_ui_adds_assembly_controls() -> None:
    assert "Assemble 9:16 video" in HTML
    assert "/api/stock-avatar/assemble" in HTML
    assert "avatar-reference" in HTML


def test_stock_avatar_ui_limits_browser_selection() -> None:
    assert "selectedStockClips.length>=6" in HTML
    assert "Select at least one stock clip." in HTML


def test_stock_avatar_ui_includes_avatar_library() -> None:
    assert "Avatar Library" in HTML
    assert "/api/avatars" in HTML
    assert "Create Avatar" in HTML
    assert "Use Avatar" in HTML


def test_stock_avatar_extension_script_loads_after_base_ui_script() -> None:
    assert HTML.index("loadHistory();") < HTML.index("const assembleButton=")
