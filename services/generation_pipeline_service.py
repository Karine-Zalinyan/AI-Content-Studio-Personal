"""Minimal end-to-end generation pipeline for the Social Content Studio MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.generation_plan import GenerationPlan
from models.project import GeneratedAsset, VideoOutput
from services.generated_video_export_service import GeneratedVideoExportService
from services.generation_asset_persistence_service import GenerationAssetPersistenceService
from services.generation_executor_service import ExecutionReport, GenerationExecutor, ProviderAdapter
from services.providers.fal_seedance import FalSeedanceAdapter


@dataclass(frozen=True)
class GenerationPipelineResult:
    """Traceable result of one provider-backed generation/export run."""

    report: ExecutionReport
    assets: tuple[GeneratedAsset, ...]
    video: VideoOutput


class GenerationPipelineService:
    """Run GenerationPlan → provider execution → persistence → MP4 export.

    The orchestration boundary deliberately owns no provider-specific planning
    logic. Provider selection remains in the GenerationPlan; the MVP defaults
    to the existing FalSeedanceAdapter for the selected Seedance path, while
    tests and future providers can inject a different adapter.
    """

    def __init__(
        self,
        *,
        adapter: ProviderAdapter | None = None,
        executor: GenerationExecutor | None = None,
        persistence: GenerationAssetPersistenceService | None = None,
        exporter: GeneratedVideoExportService | None = None,
        output_dir: str | Path = "output",
    ) -> None:
        self._adapter = adapter or FalSeedanceAdapter()
        self._executor = executor or GenerationExecutor(adapter=self._adapter)
        self._persistence = persistence or GenerationAssetPersistenceService()
        self._exporter = exporter or GeneratedVideoExportService(output_dir)

    def run(self, plan: GenerationPlan) -> GenerationPipelineResult:
        """Execute the complete MVP path and return traceable output metadata."""
        report = self._executor.execute(plan)
        if report.failed:
            failed = ", ".join(
                f"{result.job_id}: {result.error_message or 'generation failed'}"
                for result in report.failed
            )
            raise RuntimeError(f"Generation pipeline stopped before export: {failed}")

        if not report.results:
            raise ValueError("Generation pipeline cannot export an empty GenerationPlan.")

        assets = tuple(self._persistence.persist(report))
        video = self._exporter.export(report, assets)
        return GenerationPipelineResult(report=report, assets=assets, video=video)
