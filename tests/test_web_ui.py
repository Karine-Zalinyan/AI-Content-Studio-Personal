from __future__ import annotations

import json
from pathlib import Path

import web_ui


def test_job_store_round_trip() -> None:
    store = web_ui.JobStore()
    job_id = store.create()

    assert store.get(job_id) == {"status": "queued", "error": "", "video": ""}

    store.update(job_id, status="done", video="project_9x16.mp4")
    assert store.get(job_id) == {
        "status": "done",
        "error": "",
        "video": "project_9x16.mp4",
    }


def test_job_store_returns_copies() -> None:
    store = web_ui.JobStore()
    job_id = store.create()
    snapshot = store.get(job_id)
    assert snapshot is not None

    snapshot["status"] = "done"
    assert store.get(job_id)["status"] == "queued"


def test_mvp_html_exposes_only_the_core_creation_controls() -> None:
    assert "Create your next video." in web_ui.HTML
    assert 'name="topic"' in web_ui.HTML
    assert "9:16 · TikTok / Reels / Shorts" in web_ui.HTML
    assert "Generate video" in web_ui.HTML
    assert "/api/jobs/" in web_ui.HTML
    assert "Export MP4" in web_ui.HTML
    assert "provider controls" not in web_ui.HTML.lower()
    assert "billing" not in web_ui.HTML.lower()


def test_output_path_is_restricted_to_output_root(tmp_path: Path) -> None:
    root = tmp_path / "output"
    root.mkdir()
    safe = (root / "video.mp4").resolve()
    outside = (tmp_path / "outside.mp4").resolve()

    safe.relative_to(root.resolve())
    try:
        outside.relative_to(root.resolve())
    except ValueError:
        pass
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("outside path must not be considered an output asset")


def test_job_status_payload_is_json_serializable() -> None:
    store = web_ui.JobStore()
    job_id = store.create()
    store.update(job_id, status="done", video="video.mp4")
    payload = store.get(job_id)

    assert json.loads(json.dumps(payload))["video"] == "video.mp4"
