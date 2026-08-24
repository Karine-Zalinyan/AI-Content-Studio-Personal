from pathlib import Path

import pytest

from models.project import Project
from services.stock_avatar_assembly_service import StockAvatarAssemblyService


def test_requires_stock_clip() -> None:
    with pytest.raises(ValueError, match="At least one stock clip"):
        StockAvatarAssemblyService().assemble(Project(topic="demo"), [], output_path="out.mp4")


def test_rejects_non_https_stock_url() -> None:
    clips = [{"preview_url": "http://example.com/video.mp4"}]
    with pytest.raises(ValueError, match="safe HTTPS URL"):
        StockAvatarAssemblyService().assemble(Project(topic="demo"), clips, output_path="out.mp4")


def test_safe_https_url_accepts_only_https() -> None:
    assert StockAvatarAssemblyService._safe_https_url("https://example.com/a.mp4") == "https://example.com/a.mp4"
    assert StockAvatarAssemblyService._safe_https_url("http://example.com/a.mp4") is None
    assert StockAvatarAssemblyService._safe_https_url("javascript:alert(1)") is None


def test_ffmpeg_error_is_actionable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = StockAvatarAssemblyService(ffmpeg_binary="missing-ffmpeg")
    monkeypatch.setattr(service, "_download", lambda _url, destination: destination.write_bytes(b"x"))
    with pytest.raises(RuntimeError, match="FFmpeg is required"):
        service.assemble(
            Project(topic="demo"),
            [{"preview_url": "https://example.com/video.mp4"}],
            output_path=tmp_path / "out.mp4",
        )
