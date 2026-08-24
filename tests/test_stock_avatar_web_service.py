from pathlib import Path

import pytest

from services.stock_avatar_web_service import StockAvatarWebService


class FakeAssembler:
    def __init__(self) -> None:
        self.calls = []

    def assemble(self, project, stock_clips, *, avatar_reference, output_path):
        self.calls.append((project, stock_clips, avatar_reference, output_path))
        return Path(output_path)


def test_assembles_valid_browser_request(tmp_path: Path) -> None:
    assembler = FakeAssembler()
    service = StockAvatarWebService(assembler=assembler)

    project, output = service.assemble_request(
        topic="A kind delivery story",
        stock_clips=[{"preview_url": "https://example.com/clip.mp4"}],
        avatar_reference="https://example.com/avatar.png",
        output_path=tmp_path / "result.mp4",
    )

    assert project.topic == "A kind delivery story"
    assert output == tmp_path / "result.mp4"
    assert len(assembler.calls) == 1


def test_rejects_empty_topic() -> None:
    with pytest.raises(ValueError, match="Topic cannot be empty"):
        StockAvatarWebService(assembler=FakeAssembler()).assemble_request(
            topic="  ",
            stock_clips=[{"preview_url": "https://example.com/clip.mp4"}],
            avatar_reference=None,
            output_path="out.mp4",
        )


def test_rejects_more_than_six_clips() -> None:
    clips = [{"preview_url": f"https://example.com/{index}.mp4"} for index in range(7)]
    with pytest.raises(ValueError, match="maximum of 6"):
        StockAvatarWebService(assembler=FakeAssembler()).assemble_request(
            topic="demo",
            stock_clips=clips,
            avatar_reference=None,
            output_path="out.mp4",
        )


def test_rejects_non_string_avatar_reference() -> None:
    with pytest.raises(ValueError, match="Avatar reference"):
        StockAvatarWebService(assembler=FakeAssembler()).assemble_request(
            topic="demo",
            stock_clips=[{"preview_url": "https://example.com/clip.mp4"}],
            avatar_reference=123,
            output_path="out.mp4",
        )
