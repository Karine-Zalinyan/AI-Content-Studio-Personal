from services.stock_avatar_browser_api import StockAvatarBrowserRequestAdapter


def _payload(**overrides):
    payload = {
        "topic": "Kindness",
        "stock_clips": [
            {"id": "1", "preview_url": "https://cdn.example/clip.mp4", "source_url": "https://pexels.com/video/1"}
        ],
        "avatar_reference": "https://cdn.example/avatar.png",
        "output_path": "pending.mp4",
    }
    payload.update(overrides)
    return payload


def test_browser_adapter_accepts_https_avatar_and_clips() -> None:
    request = StockAvatarBrowserRequestAdapter.parse(_payload())
    assert request["avatar_reference"].startswith("https://")


def test_browser_adapter_rejects_non_https_avatar() -> None:
    try:
        StockAvatarBrowserRequestAdapter.parse(_payload(avatar_reference="http://example/avatar.png"))
    except ValueError:
        return
    raise AssertionError("non-HTTPS avatar reference must be rejected")


def test_browser_adapter_rejects_non_https_stock_urls() -> None:
    try:
        StockAvatarBrowserRequestAdapter.parse(
            _payload(stock_clips=[{"id": "1", "preview_url": "http://cdn.example/clip.mp4"}])
        )
    except ValueError:
        return
    raise AssertionError("non-HTTPS stock URL must be rejected")
