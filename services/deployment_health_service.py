"""Small, secret-safe deployment health checks for the browser MVP."""

from __future__ import annotations

from pathlib import Path


class DeploymentHealthService:
    """Report process/storage readiness without exposing provider credentials."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def status(self) -> dict[str, object]:
        storage_ready = self.output_dir.exists() and self.output_dir.is_dir()
        return {
            "status": "ok" if storage_ready else "degraded",
            "storage": "ok" if storage_ready else "unavailable",
        }
