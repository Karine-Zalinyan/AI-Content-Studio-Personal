"""Assemble persisted generated clips into one deterministic 9:16 MP4 output."""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from models.project import GeneratedAsset, VideoOutput
from services.generation_executor_service import ExecutionReport, ExecutionStatus

ClipAssembler = Callable[[Sequence[Path], Path], None]


class GeneratedVideoExportService:
    """Application-layer export boundary for persisted generated video clips."""

    def __init__(
        self,
        output_dir: str | Path = "output",
        *,
        assembler: ClipAssembler | None = None,
    ) -> None:
        self._output_dir = Path(output_dir).resolve()
        self._assembler = assembler or self._assemble_clips

    def export(self, report: ExecutionReport, assets: Sequence[GeneratedAsset]) -> VideoOutput:
        """Export completed generated assets in deterministic execution order."""
        if not report.results:
            raise ValueError("Execution report has no generated clips to export.")

        failed_jobs = [result.job_id for result in report.results if result.status == ExecutionStatus.FAILED]
        if failed_jobs:
            joined = ", ".join(failed_jobs)
            raise RuntimeError(f"Cannot export with failed generation jobs: {joined}")

        ordered_assets = self._resolve_assets(report, assets)
        if not ordered_assets:
            raise ValueError("No persisted generated clips are available for export.")

        for asset in ordered_assets:
            self._validate_asset(asset)

        destination = self._build_output_path(report.project_topic)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            self._assembler([Path(asset.file_path) for asset in ordered_assets], temporary)
            if not temporary.exists() or not temporary.is_file():
                raise RuntimeError("Generated video export did not produce an MP4 artifact.")
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

        total_duration = sum(max(asset.duration, 0.0) for asset in ordered_assets)
        return VideoOutput(
            file_path=str(destination),
            duration=int(round(total_duration)),
            resolution="9:16",
            format="mp4",
            metadata={
                "aspect_ratio": "9:16",
                "scene_numbers": [asset.scene_number for asset in ordered_assets],
                "source_files": [asset.file_path for asset in ordered_assets],
            },
        )

    def _resolve_assets(
        self,
        report: ExecutionReport,
        assets: Sequence[GeneratedAsset],
    ) -> list[GeneratedAsset]:
        assets_by_job_id = {
            str(asset.metadata.get("job_id")): asset
            for asset in assets
            if asset.metadata.get("job_id")
        }
        assets_by_scene = {asset.scene_number: asset for asset in assets}

        ordered_assets: list[GeneratedAsset] = []
        ordered_results = sorted(
            (result for result in report.results if result.status == ExecutionStatus.COMPLETED),
            key=lambda result: result.sequence,
        )
        for result in ordered_results:
            asset = assets_by_job_id.get(result.job_id) or assets_by_scene.get(result.scene_number)
            if asset is None:
                raise RuntimeError(
                    f"Missing persisted generated asset for job '{result.job_id}' (scene {result.scene_number})."
                )
            ordered_assets.append(asset)
        return ordered_assets

    def _validate_asset(self, asset: GeneratedAsset) -> None:
        source = Path(asset.file_path)
        if not source.exists() or not source.is_file():
            raise RuntimeError(f"Generated asset is missing or unreadable: {source}")
        try:
            with source.open("rb"):
                pass
        except OSError as exc:
            raise RuntimeError(f"Generated asset is missing or unreadable: {source}") from exc

        aspect_ratio = self._aspect_ratio(asset)
        if aspect_ratio != "9:16":
            raise RuntimeError(
                f"Generated asset '{source.name}' is not 9:16-compatible (found '{aspect_ratio or 'unknown'}')."
            )

    def _build_output_path(self, project_topic: str) -> Path:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", project_topic.strip())
        slug = re.sub(r"_+", "_", slug).strip("_")
        return self._output_dir / f"{slug or 'project'}_9x16.mp4"

    def _assemble_clips(self, clips: Sequence[Path], destination: Path) -> None:
        if len(clips) == 1:
            shutil.copyfile(clips[0], destination)
            return

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is required to export multiple generated clips.")

        manifest = destination.with_suffix(".txt")
        try:
            lines = []
            for path in clips:
                escaped = str(path).replace("'", "'\\''")
                lines.append(f"file '{escaped}'")
            manifest.write_text(
                "\n".join(lines),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(manifest),
                    "-c",
                    "copy",
                    str(destination),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        finally:
            manifest.unlink(missing_ok=True)

        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip() or "unknown ffmpeg error"
            raise RuntimeError(f"Generated video export failed: {details}")

    @staticmethod
    def _aspect_ratio(asset: GeneratedAsset) -> str:
        raw = str(asset.metadata.get("aspect_ratio", "") or "").strip()
        normalized = GeneratedVideoExportService._normalize_ratio(raw)
        if normalized:
            return normalized

        resolution = asset.resolution.strip()
        normalized = GeneratedVideoExportService._normalize_ratio(resolution)
        if normalized:
            return normalized

        match = re.search(r"(\d+)\s*[xX×]\s*(\d+)", resolution)
        if not match:
            return ""
        return GeneratedVideoExportService._normalize_ratio(f"{match.group(1)}:{match.group(2)}")

    @staticmethod
    def _normalize_ratio(value: str) -> str:
        match = re.search(r"(\d+)\s*[:xX×]\s*(\d+)", value)
        if not match:
            return ""

        width = int(match.group(1))
        height = int(match.group(2))
        if width == 0 or height == 0:
            return ""

        def gcd(left: int, right: int) -> int:
            while right:
                left, right = right, left % right
            return left

        divisor = gcd(width, height)
        return f"{width // divisor}:{height // divisor}"
