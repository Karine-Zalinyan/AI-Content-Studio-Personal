from pathlib import Path

import pytest

from services.stock_avatar_browser_api import StockAvatarBrowserRequestAdapter


def test_parse_accepts_json_clip_payload() -> None:
    result = StockAvatarBrowserRequestAdapter.parse(
        {
            "topic": "Kindness",
            "stock_clips": '[{"id": "clip-1"}]',
            "avatar_reference": "avatar.png",
            "output_path": "output/kindness.mp4",
        }
    )

    assert result["topic"] == "Kindness"
    assert result["stock_clips"] == [{"id": "clip-1"}]
    assert result["avatar_reference"] == "avatar.png"
    assert result["output_path"] == Path("output/kindness.mp4")


def test_parse_rejects_empty_clip_selection() -> None:
    with pytest.raises(ValueError, match="At least one stock clip"):
        StockAvatarBrowserRequestAdapter.parse(
            {"topic": "Kindness", "stock_clips": [], "output_path": "output/a.mp4"}
        )


def test_parse_rejects_more_than_six_clips() -> None:
    clips = [{"id": str(index)} for index in range(7)]
    with pytest.raises(ValueError, match="No more than 6"):
        StockAvatarBrowserRequestAdapter.parse(
            {"topic": "Kindness", "stock_clips": clips, "output_path": "output/a.mp4"}
        )


def test_parse_rejects_invalid_clip_json() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        StockAvatarBrowserRequestAdapter.parse(
            {"topic": "Kindness", "stock_clips": "not-json", "output_path": "output/a.mp4"}
        )
