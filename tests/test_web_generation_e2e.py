from __future__ import annotations

import json
import threading
import time
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace

import web_ui
from services.project_history_service import ProjectHistoryService
from services.project_history_web_service import ProjectHistoryWebService


class FakePipeline:
    def __init__(self, output_dir: Path, *, fail: bool = False) -> None:
        self.output_dir = output_dir
        self.fail = fail

    def run(self, plan: object) -> SimpleNamespace:
        if self.fail:
            raise RuntimeError("mock generation failure")
        video = self.output_dir / "e2e" / "generated.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"fake-mp4")
        return SimpleNamespace(
            video=SimpleNamespace(
                file_path=str(video),
                metadata={"aspect_ratio": "9:16", "provider": "mock"},
            )
        )


def _start_server(monkeypatch, tmp_path: Path, *, fail: bool = False):
    history = ProjectHistoryService(tmp_path / "studio.db")
    history_web = ProjectHistoryWebService(history, tmp_path)
    monkeypatch.setattr(web_ui, "HISTORY", history)
    monkeypatch.setattr(web_ui, "HISTORY_WEB", history_web)
    monkeypatch.setattr(web_ui, "JOBS", web_ui.JobStore())
    monkeypatch.setattr(web_ui, "StoryboardContextService", lambda: SimpleNamespace(create=lambda project: project))
    monkeypatch.setattr(web_ui, "GenerationPlanner", lambda: SimpleNamespace(create=lambda storyboard: storyboard))
    monkeypatch.setattr(
        web_ui,
        "GenerationPipelineService",
        lambda output_dir: FakePipeline(output_dir, fail=fail),
    )

    server = web_ui.ThreadingHTTPServer(("127.0.0.1", 0), web_ui.StudioHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, history, thread


def _post_generate(server, topic: str) -> dict[str, object]:
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    body = f"topic={topic.replace(' ', '+')}".encode()
    connection.request(
        "POST",
        "/generate",
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Content-Length": str(len(body))},
    )
    response = connection.getresponse()
    payload = json.loads(response.read())
    assert response.status == 202
    return payload


def _poll_job(server, job_id: str) -> dict[str, object]:
    deadline = time.time() + 3
    while time.time() < deadline:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        connection.request("GET", f"/api/jobs/{job_id}")
        response = connection.getresponse()
        payload = json.loads(response.read())
        if payload["status"] in {"done", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError("job did not reach a terminal state")


def test_browser_generation_persists_and_survives_restart(monkeypatch, tmp_path: Path) -> None:
    server, history, _ = _start_server(monkeypatch, tmp_path)
    try:
        created = _post_generate(server, "A child helps a tired courier")
        job = _poll_job(server, str(created["job_id"]))

        assert job["status"] == "done"
        assert job["video_url"] == "/output/e2e/generated.mp4"

        recent = history.list_recent()
        assert len(recent) == 1
        assert recent[0]["topic"] == "A child helps a tired courier"
        assert recent[0]["status"] == "done"
        assert recent[0]["output_path"] == "e2e/generated.mp4"
        assert recent[0]["output_metadata"]["aspect_ratio"] == "9:16"

        # Simulate a process restart: build new persistence/projection objects
        # from the same SQLite database and verify the generated asset is still visible.
        restarted_history = ProjectHistoryService(tmp_path / "studio.db")
        restarted_web = ProjectHistoryWebService(restarted_history, tmp_path)
        restarted = restarted_web.recent()
        assert restarted[0]["status"] == "done"
        assert restarted[0]["video_url"] == "/output/e2e/generated.mp4"
    finally:
        server.shutdown()
        server.server_close()


def test_browser_generation_failure_is_persisted(monkeypatch, tmp_path: Path) -> None:
    server, history, _ = _start_server(monkeypatch, tmp_path, fail=True)
    try:
        created = _post_generate(server, "A generation that should fail")
        job = _poll_job(server, str(created["job_id"]))

        assert job["status"] == "failed"
        assert "mock generation failure" in str(job["error"])

        recent = history.list_recent()
        assert len(recent) == 1
        assert recent[0]["status"] == "failed"
        assert recent[0]["error_message"] == "mock generation failure"
        assert recent[0]["output_path"] is None
    finally:
        server.shutdown()
        server.server_close()
