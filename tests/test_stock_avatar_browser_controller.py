from pathlib import Path

from models.project import Project
from services.project_history_service import ProjectHistoryService
from services.stock_avatar_browser_controller import StockAvatarBrowserController


class FakeAssembly:
    def assemble_request(self, *, topic, stock_clips, avatar_reference, output_path):
        project = Project(topic=topic)
        project.video.metadata = {
            "assembly_mode": "stock_avatar",
            "avatar_reference": avatar_reference or "",
        }
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-mp4")
        return project, output


def test_controller_persists_completed_stock_avatar_job(tmp_path):
    history = ProjectHistoryService(tmp_path / "studio.db")
    controller = StockAvatarBrowserController(history, assembly=FakeAssembly())

    result = controller.assemble(
        topic="A kind moment",
        stock_clips=[{"preview_url": "https://cdn.example/clip.mp4"}],
        avatar_reference="https://cdn.example/avatar.png",
        output_path=tmp_path / "kindness.mp4",
    )

    assert result["status"] == "done"
    assert result["output_path"] == "kindness.mp4"
    job = history.get_job(result["job_id"])
    assert job is not None
    assert job["topic"] == "A kind moment"
    assert job["status"] == "done"
    assert job["output_path"] == "kindness.mp4"
    assert job["output_metadata"]["assembly_mode"] == "stock_avatar"
    assert job["output_metadata"]["stock_clip_count"] == 1


def test_controller_keeps_avatar_reference_out_of_project_identity(tmp_path):
    history = ProjectHistoryService(tmp_path / "studio.db")
    controller = StockAvatarBrowserController(history, assembly=FakeAssembly())

    result = controller.assemble(
        topic="Avatar test",
        stock_clips=[{"preview_url": "https://cdn.example/clip.mp4"}],
        avatar_reference="https://cdn.example/avatar.png",
        output_path=tmp_path / "avatar.mp4",
    )

    job = history.get_job(result["job_id"])
    assert job is not None
    assert job["avatar_id"] is None
    assert job["output_metadata"]["avatar_reference"] == "https://cdn.example/avatar.png"
