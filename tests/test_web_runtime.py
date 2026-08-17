from __future__ import annotations

import pytest

import run_web


def test_port_defaults_to_8787(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORT", raising=False)
    assert run_web._port() == 8787


def test_port_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "9000")
    assert run_web._port() == 9000


@pytest.mark.parametrize("value", ["0", "65536", "not-a-port"])
def test_port_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("PORT", value)
    with pytest.raises(ValueError):
        run_web._port()
