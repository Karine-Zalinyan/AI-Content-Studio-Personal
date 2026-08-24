"""Non-secret readiness checks for the first real provider smoke test."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReadinessReport:
    """Safe-to-log provider/runtime readiness result."""

    ready: bool
    missing: tuple[str, ...]
    output_dir: str


def check_provider_runtime_readiness(
    *,
    env: dict[str, str] | None = None,
    output_dir: str | Path = "output",
) -> ReadinessReport:
    """Check required runtime configuration without ever returning secret values."""

    source = os.environ if env is None else env
    missing = tuple(name for name in ("FAL_KEY",) if not source.get(name, "").strip())
    resolved_output = Path(output_dir).resolve()
    return ReadinessReport(
        ready=not missing,
        missing=missing,
        output_dir=str(resolved_output),
    )
