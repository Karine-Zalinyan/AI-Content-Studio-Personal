from pathlib import Path
from subprocess import CompletedProcess

import pytest

from services.stock_video_composer_service import StockVideoComposerService


def test_compose_downloads_selected_clips_and_builds_youtube_command(tmp_path: Path) -> None:
    downloads: list[tuple[str, Path]] = []
    commands: list[list[str]] = []

    def download(url: str, destination: Path) -> None:
        downloads.append((url, destination))
        destination.write_bytes(b"clip")

    def runner(command, **kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"mp4")
        return CompletedProcess(command, 0, stdout=b"", stderr=b"")

    output = tmp_path / "youtube.mp4"
    result = StockVideoComposerService(downloader=download, runner=runner).compose(
        [
            {"preview_url": "https://cdn.example/one.mp4"},
            {"source_url": "https://cdn.example/two.mp4"},
        ],
        output_path=output,
        duration_seconds=60,
    )

    assert result == output.resolve()
    assert output.read_bytes() == b"mp4"
    assert [url for url, _ in downloads] == [
        "https://cdn.example/one.mp4",
        "https://cdn.example/two.mp4",
    ]
    command = commands[0]
    assert command[:7] == ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i"]
    assert command[7].endswith("concat.txt")
    assert any("1920:1080" in argument for argument in command)
    assert "-t" in command
    assert command[command.index("-t") + 1] == "60"
    assert command[-1] == str(output.resolve())


def test_compose_rejects_non_https_urls(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="safe HTTPS"):
        StockVideoComposerService().compose(
            [{"preview_url": "http://cdn.example/clip.mp4"}],
            output_path=tmp_path / "video.mp4",
        )


def test_compose_rejects_too_many_clips(tmp_path: Path) -> None:
    clips = [{"preview_url": f"https://cdn.example/{index}.mp4"} for index in range(13)]
    with pytest.raises(ValueError, match="maximum of 12"):
        StockVideoComposerService().compose(clips, output_path=tmp_path / "video.mp4")


def test_compose_requires_positive_duration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duration_seconds must be positive"):
        StockVideoComposerService().compose(
            [{"preview_url": "https://cdn.example/clip.mp4"}],
            output_path=tmp_path / "video.mp4",
            duration_seconds=0,
        )
