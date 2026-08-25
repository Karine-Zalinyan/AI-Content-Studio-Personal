"""Assemble a free vertical video from stock clips and a canonical Avatar image."""

from __future__ import annotations

import subprocess
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse

from models.project import Project


class StockAvatarAssemblyService:
    """Build a deterministic 9:16 MP4 without invoking a paid generation provider.

    Stock clips are downloaded from HTTPS URLs returned by the stock provider. A
    canonical Avatar visual reference may be overlaid on each clip. FFmpeg is
    intentionally used as an external runtime dependency so this service does
    not add another Python media stack to the project.
    """

    MAX_STOCK_BYTES = 50 * 1024 * 1024
    MAX_AVATAR_BYTES = 10 * 1024 * 1024
    DOWNLOAD_CHUNK_BYTES = 64 * 1024

    def __init__(self, ffmpeg_binary: str = "ffmpeg", timeout: int = 60) -> None:
        self.ffmpeg_binary = ffmpeg_binary
        self.timeout = timeout

    def assemble(
        self,
        project: Project,
        stock_clips: list[dict[str, Any]],
        *,
        avatar_reference: str | None = None,
        output_path: str | Path,
    ) -> Path:
        if not stock_clips:
            raise ValueError("At least one stock clip is required")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        avatar_url = self._safe_https_url(avatar_reference)

        with TemporaryDirectory(prefix="stock-avatar-") as temp_dir:
            root = Path(temp_dir)
            rendered: list[Path] = []
            avatar_path: Path | None = None
            if avatar_url:
                avatar_path = root / "avatar.png"
                self._download(avatar_url, avatar_path, max_bytes=self.MAX_AVATAR_BYTES, resource_type="Avatar")

            for index, clip in enumerate(stock_clips, start=1):
                source = self._safe_https_url(clip.get("preview_url") or clip.get("source_url"))
                if not source:
                    raise ValueError(f"Stock clip {index} has no safe HTTPS URL")
                clip_path = root / f"clip-{index}.mp4"
                self._download(source, clip_path, max_bytes=self.MAX_STOCK_BYTES, resource_type=f"Stock clip {index}")
                rendered_path = root / f"rendered-{index}.mp4"
                self._render_clip(clip_path, rendered_path, avatar_path)
                rendered.append(rendered_path)

            concat_file = root / "concat.txt"
            concat_file.write_text(
                "\n".join(f"file '{path.as_posix()}'" for path in rendered),
                encoding="utf-8",
            )
            self._run(
                [
                    self.ffmpeg_binary,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
                    "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                    "-r",
                    "30",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-an",
                    str(output),
                ]
            )

        project.stock = {"clips": stock_clips, "mode": "free_stock"}
        project.video.file_path = str(output)
        project.video.resolution = "1080x1920"
        project.video.format = "mp4"
        project.video.metadata = {"assembly_mode": "stock_avatar", "avatar_reference": avatar_url or ""}
        return output

    def _render_clip(self, source: Path, output: Path, avatar: Path | None) -> None:
        base_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        command = [self.ffmpeg_binary, "-y", "-i", str(source)]
        if avatar:
            command += ["-i", str(avatar), "-filter_complex", f"[0:v]{base_filter}[bg];[1:v]scale=260:-1[av];[bg][av]overlay=W-w-32:H-h-32"]
        else:
            command += ["-vf", base_filter]
        command += ["-t", "8", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(output)]
        self._run(command)

    def _download(self, url: str, destination: Path, *, max_bytes: int, resource_type: str) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "AI-Content-Studio/1.0"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise RuntimeError(f"{resource_type} exceeds the {max_bytes} byte download limit")

            total = 0
            with destination.open("wb") as output:
                while True:
                    remaining = max_bytes - total
                    if remaining <= 0:
                        raise RuntimeError(f"{resource_type} exceeds the {max_bytes} byte download limit")
                    chunk = response.read(min(self.DOWNLOAD_CHUNK_BYTES, remaining))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise RuntimeError(f"{resource_type} exceeds the {max_bytes} byte download limit")
                    output.write(chunk)

    def _run(self, command: list[str]) -> None:
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=self.timeout)
        except FileNotFoundError as exc:
            raise RuntimeError("FFmpeg is required for stock/avatar assembly") from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", errors="replace")[-1200:]
            raise RuntimeError(f"FFmpeg assembly failed: {detail}") from exc

    @staticmethod
    def _safe_https_url(value: Any) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        parsed = urlparse(value)
        return value if parsed.scheme == "https" and parsed.netloc else None
