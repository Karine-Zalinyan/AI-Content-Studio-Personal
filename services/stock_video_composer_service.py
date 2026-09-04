"""Assemble selected free stock clips into a YouTube-ready MP4."""

from __future__ import annotations

import shutil
import subprocess
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Sequence
from urllib.parse import urlparse


Runner = Callable[..., subprocess.CompletedProcess[bytes]]
Downloader = Callable[[str, Path], None]


class StockVideoComposerService:
    """Download selected HTTPS stock clips and compose a deterministic MP4.

    This is intentionally provider-agnostic: stock search/planning remains
    outside the composer. The service only accepts validated HTTPS media URLs,
    bounds downloads, and delegates media assembly to FFmpeg.
    """

    max_clips = 12
    max_clip_bytes = 50 * 1024 * 1024
    output_width = 1920
    output_height = 1080

    def __init__(
        self,
        *,
        ffmpeg_binary: str = "ffmpeg",
        timeout: int = 60,
        downloader: Downloader | None = None,
        runner: Runner | None = None,
    ) -> None:
        self.ffmpeg_binary = ffmpeg_binary
        self.timeout = timeout
        self._downloader = downloader or self._download
        self._runner = runner or subprocess.run

    def compose(
        self,
        stock_clips: Sequence[dict[str, Any]],
        *,
        output_path: str | Path,
        duration_seconds: int | None = None,
    ) -> Path:
        """Compose selected stock clips into one landscape YouTube MP4."""
        if not stock_clips:
            raise ValueError("At least one stock clip is required")
        if len(stock_clips) > self.max_clips:
            raise ValueError(f"A maximum of {self.max_clips} stock clips is supported")
        if duration_seconds is not None and duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        with TemporaryDirectory(prefix="stock-compose-") as temp_dir:
            root = Path(temp_dir)
            local_clips: list[Path] = []
            for index, clip in enumerate(stock_clips, start=1):
                url = self._safe_https_url(clip.get("preview_url") or clip.get("source_url"))
                if not url:
                    raise ValueError(f"Stock clip {index} has no safe HTTPS media URL")
                local_path = root / f"clip-{index}.mp4"
                self._downloader(url, local_path)
                local_clips.append(local_path)

            concat_file = root / "concat.txt"
            concat_file.write_text(
                "\n".join(f"file '{path.as_posix()}'" for path in local_clips),
                encoding="utf-8",
            )

            command = [
                self.ffmpeg_binary,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-vf",
                "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1",
                "-r",
                "30",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
            ]
            if duration_seconds is not None:
                command.extend(["-t", str(duration_seconds)])
            command.append(str(output))
            self._run(command)

        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("Stock video composition did not produce an MP4 artifact")
        return output

    def _download(self, url: str, destination: Path) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "AI-Content-Studio/1.0"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            declared = response.headers.get("Content-Length")
            if declared:
                try:
                    if int(declared) > self.max_clip_bytes:
                        raise ValueError("Stock clip exceeds the maximum download size")
                except ValueError as exc:
                    if str(exc) == "Stock clip exceeds the maximum download size":
                        raise

            written = 0
            with destination.open("wb") as target:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > self.max_clip_bytes:
                        raise ValueError("Stock clip exceeds the maximum download size")
                    target.write(chunk)

    def _run(self, command: list[str]) -> None:
        try:
            completed = self._runner(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("FFmpeg is required for stock video composition") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or b"").decode("utf-8", errors="replace")[-1200:]
            raise RuntimeError(f"Stock video composition failed: {detail or 'unknown ffmpeg error'}")

    @staticmethod
    def _safe_https_url(value: Any) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        parsed = urlparse(value.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            return None
        return value.strip()
