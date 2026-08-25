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
    monkeypatch.setattr(service, "_download", lambda _url, destination, **_kwargs: destination.write_bytes(b"x"))
    with pytest.raises(RuntimeError, match="FFmpeg is required"):
        service.assemble(
            Project(topic="demo"),
            [{"preview_url": "https://example.com/video.mp4"}],
            output_path=tmp_path / "out.mp4",
        )


def test_download_rejects_large_content_length(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeHeaders:
        def get(self, name: str) -> str | None:
            return str(StockAvatarAssemblyService.MAX_AVATAR_BYTES + 1) if name == "Content-Length" else None

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: FakeResponse())
    service = StockAvatarAssemblyService()
    with pytest.raises(RuntimeError, match="Avatar exceeds"):
        service._download(
            "https://example.com/avatar.png",
            tmp_path / "avatar.png",
            max_bytes=service.MAX_AVATAR_BYTES,
            resource_type="Avatar",
        )


def test_download_streaming_rejects_body_over_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeHeaders:
        def get(self, _name: str) -> None:
            return None

    class FakeResponse:
        headers = FakeHeaders()
        chunks = [b"1234", b"5678", b"9"]

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            return self.chunks.pop(0) if self.chunks else b""

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: FakeResponse())
    service = StockAvatarAssemblyService()
    with pytest.raises(RuntimeError, match="Stock clip exceeds"):
        service._download(
            "https://example.com/video.mp4",
            tmp_path / "video.mp4",
            max_bytes=8,
            resource_type="Stock clip",
        )
