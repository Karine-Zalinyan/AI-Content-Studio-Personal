"""Assemble persisted generated clips into one deterministic 9:16 MP4 output."""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from models.project import GeneratedAsset, VideoOutput
from services.generation_executor_service import ExecutionReport, ExecutionStatus

# The assembler must write the final MP4 bytes to the provided destination path.
ClipAssembler = Callable[[Sequence[GeneratedAsset], Path], None]


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

        incomplete_jobs = [
            f"{result.job_id} ({result.status.value})"
            for result in report.results
            if result.status != ExecutionStatus.COMPLETED
        ]
        if incomplete_jobs:
            joined = ", ".join(incomplete_jobs)
            raise RuntimeError(f"Cannot export with non-completed generation jobs: {joined}")

        ordered_assets = self._resolve_assets(report, assets)
        for asset in ordered_assets:
            self._validate_asset(asset)
        output_resolution = self._output_resolution(ordered_assets)

        destination = self._build_output_path(report.project_topic)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            self._assembler(ordered_assets, temporary)
            if not temporary.exists() or not temporary.is_file():
                raise RuntimeError("Generated video export did not produce an MP4 artifact.")
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

        total_duration = sum(max(asset.duration, 0.0) for asset in ordered_assets)
        return VideoOutput(
            file_path=str(destination.resolve()),
            duration=int(round(total_duration)),
            resolution=output_resolution,
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
        scene_assets: dict[int, list[GeneratedAsset]] = {}
        for asset in assets:
            scene_assets.setdefault(asset.scene_number, []).append(asset)

        ordered_assets: list[GeneratedAsset] = []
        ordered_results = sorted(
            (result for result in report.results if result.status == ExecutionStatus.COMPLETED),
            key=lambda result: result.sequence,
        )
        for result in ordered_results:
            asset = assets_by_job_id.get(result.job_id)
            if asset is None:
                scene_matches = scene_assets.get(result.scene_number, [])
                if len(scene_matches) > 1:
                    raise RuntimeError(
                        f"Multiple persisted generated assets found for scene {result.scene_number}."
                    )
                asset = scene_matches[0] if scene_matches else None
            if asset is None:
                raise RuntimeError(
                    f"Missing persisted generated asset for job '{result.job_id}' (scene {result.scene_number})."
                )
            ordered_assets.append(asset)
        return ordered_assets

    def _validate_asset(self, asset: GeneratedAsset) -> None:
        source = Path(asset.file_path)
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

    def _assemble_clips(self, clips: Sequence[GeneratedAsset], destination: Path) -> None:
        clip_paths = [Path(asset.file_path) for asset in clips]
        if len(clip_paths) == 1:
            shutil.copyfile(clip_paths[0], destination)
            return

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is required to export multiple generated clips.")

        target_width, target_height = self._output_dimensions(clips)
        filter_parts = []
        concat_inputs = []
        command = [ffmpeg, "-y"]
        for index, clip_path in enumerate(clip_paths):
            command.extend(["-i", str(clip_path)])
            filter_parts.append(
                f"[{index}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
                "setsar=1,format=yuv420p,setpts=PTS-STARTPTS"
                f"[v{index}]"
            )
            concat_inputs.append(f"[v{index}]")

        filter_parts.append(f"{''.join(concat_inputs)}concat=n={len(clip_paths)}:v=1:a=0[vout]")
        command.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                "[vout]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(destination),
            ]
        )
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip() or "unknown ffmpeg error"
            raise RuntimeError(f"Generated video export failed: {details}")

    def _output_resolution(self, assets: Sequence[GeneratedAsset]) -> str:
        width, height = self._output_dimensions(assets)
        return f"{width}x{height}"

    def _output_dimensions(self, assets: Sequence[GeneratedAsset]) -> tuple[int, int]:
        dimensions: list[tuple[int, int]] = []
        for asset in assets:
            width, height = self._resolution_dimensions(asset)
            if width == 0 or height == 0:
                source = Path(asset.file_path).name
                raise RuntimeError(f"Generated asset '{source}' is missing an exportable resolution.")
            dimensions.append((width, height))
        return min(dimensions, key=lambda pair: (pair[0] * pair[1], pair[0], pair[1]))

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
        return ""

    @staticmethod
    def _resolution_dimensions(asset: GeneratedAsset) -> tuple[int, int]:
        match = re.search(r"(\d+)\s*[xX×]\s*(\d+)", asset.resolution.strip())
        if not match:
            return (0, 0)
        return int(match.group(1)), int(match.group(2))

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
