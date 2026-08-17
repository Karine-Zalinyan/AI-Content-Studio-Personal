from pathlib import Path

from services.project_history_service import ProjectHistoryService


def test_project_and_job_survive_service_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "studio.sqlite3"
    first = ProjectHistoryService(db_path)
    project_id = first.create_project(
        "A child helps a tired courier",
        universe_id="universe-1",
        avatar_id="avatar-1",
        location_id="location-1",
    )
    job_id = first.create_job(project_id)
    first.update_job(
        job_id,
        status="completed",
        output_path="My_Project_9x16.mp4",
        output_metadata={"aspect_ratio": "9:16", "scene_numbers": [1, 2, 3]},
    )

    second = ProjectHistoryService(db_path)
    job = second.get_job(job_id)
    assert job is not None
    assert job["project_id"] == project_id
    assert job["topic"] == "A child helps a tired courier"
    assert job["universe_id"] == "universe-1"
    assert job["avatar_id"] == "avatar-1"
    assert job["location_id"] == "location-1"
    assert job["status"] == "completed"
    assert job["output_path"] == "My_Project_9x16.mp4"
    assert job["output_metadata"]["aspect_ratio"] == "9:16"


def test_failed_jobs_remain_visible(tmp_path: Path) -> None:
    store = ProjectHistoryService(tmp_path / "studio.sqlite3")
    project_id = store.create_project("Failure test")
    job_id = store.create_job(project_id)
    store.update_job(job_id, status="failed", error_message="provider unavailable")

    history = store.list_recent()
    assert len(history) == 1
    assert history[0]["status"] == "failed"
    assert history[0]["error_message"] == "provider unavailable"
