from pathlib import Path

from services.project_history_service import ProjectHistoryService
from services.project_history_web_service import ProjectHistoryWebService


def test_recent_projects_are_ui_safe_and_keep_universe_metadata(tmp_path: Path) -> None:
    store = ProjectHistoryService(tmp_path / "studio.sqlite3")
    project_id = store.create_project(
        "A child helps a courier",
        universe_id="universe-1",
        avatar_id="avatar-1",
        location_id="location-1",
    )
    job_id = store.create_job(project_id)
    store.update_job(job_id, status="completed", output_path="clip.mp4")

    view = ProjectHistoryWebService(store, tmp_path / "output")
    recent = view.recent()

    assert recent[0]["project_id"] == project_id
    assert recent[0]["universe_id"] == "universe-1"
    assert recent[0]["avatar_id"] == "avatar-1"
    assert recent[0]["location_id"] == "location-1"
    assert recent[0]["video_url"] == "/output/clip.mp4"


def test_video_url_rejects_paths_outside_output_root(tmp_path: Path) -> None:
    store = ProjectHistoryService(tmp_path / "studio.sqlite3")
    view = ProjectHistoryWebService(store, tmp_path / "output")

    assert view.video_url("../secret.mp4") is None
    assert view.video_url(str(tmp_path / "secret.mp4")) is None
