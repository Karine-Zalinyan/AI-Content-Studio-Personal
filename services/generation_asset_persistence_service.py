"""Persist successful generation results as local GeneratedAsset records."""

from __future__ import annotations

import re
from pathlib import Path

import httpx

from models.project import GeneratedAsset
from services.generation_executor_service import ExecutionReport, ExecutionStatus


class GenerationAssetPersistenceService:
    """Download successful provider assets into a deterministic output directory."""

    def __init__(
        self,
        output_dir: str | Path = "output/generated",
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._output_dir = Path(output_dir).resolve()
        self._client = http_client

    def persist(self, report: ExecutionReport) -> list[GeneratedAsset]:
        """Persist successful results without mutating the execution report."""
        assets: list[GeneratedAsset] = []
        self._output_dir.mkdir(parents=True, exist_ok=True)

        for result in report.results:
            if result.status != ExecutionStatus.COMPLETED:
                continue
            asset_url = result.provider_response.get("asset_url")
            if not asset_url:
                raise RuntimeError(f"Execution result '{result.job_id}' has no asset URL.")

            provider = str(result.provider_response.get("provider", "provider"))
            filename = self._safe_filename(result.scene_number, result.job_id)
            destination = self._output_dir / filename
            self._download(asset_url, destination)

            assets.append(
                GeneratedAsset(
                    scene_number=result.scene_number,
                    provider=provider,
                    file_path=str(destination),
                    duration=float(result.provider_response.get("duration", 0)),
                    resolution=str(result.provider_response.get("resolution", "")),
                    metadata={
                        "job_id": result.job_id,
                        "shot_id": result.shot_id,
                        "sequence": result.sequence,
                        "request_id": result.provider_response.get("request_id", ""),
                        "asset_url": asset_url,
                        "content_type": result.provider_response.get("content_type", "video/mp4"),
                    },
                )
            )
        return assets

    def _download(self, url: str, destination: Path) -> None:
        client = self._client or httpx.Client(timeout=300.0, follow_redirects=True)
        owns_client = self._client is None
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            response = client.get(url)
            response.raise_for_status()
            temporary.write_bytes(response.content)
            temporary.replace(destination)
        except httpx.HTTPError as exc:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Generated asset download failed: {exc}") from exc
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Generated asset could not be saved: {exc}") from exc
        finally:
            if owns_client:
                client.close()

    @staticmethod
    def _safe_filename(scene_number: int, job_id: str) -> str:
        safe_job_id = re.sub(r"[^A-Za-z0-9._-]", "_", job_id)
        return f"scene_{scene_number:04d}_{safe_job_id}.mp4"
