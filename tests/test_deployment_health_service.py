from pathlib import Path

from services.deployment_health_service import DeploymentHealthService


def test_health_reports_ready_storage(tmp_path: Path) -> None:
    result = DeploymentHealthService(tmp_path).status()
    assert result == {"status": "ok", "storage": "ok"}


def test_health_reports_unavailable_storage(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    result = DeploymentHealthService(missing).status()
    assert result == {"status": "degraded", "storage": "unavailable"}


def test_health_never_reports_provider_secret_values(tmp_path: Path) -> None:
    result = DeploymentHealthService(tmp_path).status()
    assert "FAL_KEY" not in str(result)
    assert "PEXELS_API_KEY" not in str(result)
