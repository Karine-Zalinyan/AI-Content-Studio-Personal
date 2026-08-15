"""Focused tests for the AI Avatar MVP domain and persistence boundary."""

from models.project import Project
from models.universe import Avatar, CharacterBible, Universe
from services.avatar_repository import AvatarRepository


def make_avatar() -> Avatar:
    return Avatar(
        name="Mia",
        role="protagonist",
        bible=CharacterBible(
            appearance="Cream-white plush character with amber-brown eyes",
            personality="Curious, kind, brave",
            generation_description="Keep the canonical appearance and proportions consistent across every generation.",
            visual_reference="refs/mia.png",
            visual_reference_metadata={"source": "canonical", "version": "1.0"},
        ),
    )


def test_avatar_creation_and_canonical_bible() -> None:
    avatar = make_avatar()
    assert avatar.id
    assert avatar.bible.personality == "Curious, kind, brave"
    assert avatar.bible.generation_description.startswith("Keep the canonical")


def test_avatar_round_trip_persistence(tmp_path) -> None:
    repository = AvatarRepository(tmp_path / "avatars.json")
    avatar = make_avatar()

    repository.create(avatar)
    restored = repository.get(avatar.id)

    assert restored is not None
    assert restored.id == avatar.id
    assert restored.bible.model_dump() == avatar.bible.model_dump()


def test_avatar_update_preserves_stable_identity(tmp_path) -> None:
    repository = AvatarRepository(tmp_path / "avatars.json")
    avatar = make_avatar()
    repository.create(avatar)

    avatar.bible.personality = "Curious, kind, brave, determined"
    updated = repository.update(avatar)

    assert updated.id == avatar.id
    assert repository.get(avatar.id).bible.personality.endswith("determined")


def test_avatar_is_the_same_canonical_character_used_by_universe() -> None:
    avatar = make_avatar()
    universe = Universe(name="Test Universe")
    universe.characters.append(avatar)
    project = Project(topic="Mia helps a friend")

    assert universe.get_character(avatar.id) is avatar
    assert project.universe_ref is None
    assert universe.characters[0].bible.generation_description == avatar.bible.generation_description


def test_repository_delete_and_duplicate_guard(tmp_path) -> None:
    repository = AvatarRepository(tmp_path / "avatars.json")
    avatar = make_avatar()
    repository.create(avatar)

    try:
        repository.create(avatar)
        assert False, "duplicate Avatar IDs must be rejected"
    except ValueError:
        pass

    assert repository.delete(avatar.id) is True
    assert repository.get(avatar.id) is None
    assert repository.delete(avatar.id) is False
