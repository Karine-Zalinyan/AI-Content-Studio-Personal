from services.provider_runtime_readiness import check_provider_runtime_readiness


def test_readiness_reports_missing_provider_key_without_secret_value() -> None:
    report = check_provider_runtime_readiness(env={}, output_dir="output")

    assert report.ready is False
    assert report.missing == ("FAL_KEY",)
    assert "FAL_KEY" not in report.output_dir


def test_readiness_is_ready_when_provider_key_is_present() -> None:
    report = check_provider_runtime_readiness(
        env={"FAL_KEY": "test-only-secret"},
        output_dir="output",
    )

    assert report.ready is True
    assert report.missing == ()


def test_readiness_does_not_echo_secret_value() -> None:
    secret = "super-secret-test-value"
    report = check_provider_runtime_readiness(
        env={"FAL_KEY": secret},
        output_dir="output",
    )

    assert secret not in repr(report)
