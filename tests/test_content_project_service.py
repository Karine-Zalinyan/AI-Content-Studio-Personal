"""Focused tests for the Avatar → Content Project application boundary."""

import copy

import pytest

from models.project import Project
from models.universe import Avatar, CharacterBible, Location, LocationBible, Universe
from services.content_project_service import ContentProjectService


def make_universe() -> tuple[Universe, Avatar, Location]:
    avatar = Avatar(
        name="Mia",
        role="protagonist",
        bible=CharacterBible(
            appearance="Cream-white plush character with amber-brown eyes",
            personality="Curious, kind, brave",
            generation_description="Keep the canonical appearance and proportions consistent.",
        ),
    )
    location = Location(
        name="Main Hall",
        location_type="interior",
        bible=LocationBible(description="A warm central gathering space."),
    )
    return Universe(name="Endless House", characters=[avatar], locations=[location]), avatar, location


def test_avatar_creates_project_with_canonical_universe_context() -> None:
    universe, avatar, _ = make_universe()

    project = ContentProjectService().create_from_avatar(
        "Mia helps a friend", universe, avatar.id
    )

    assert project.topic == "Mia helps a friend"
    assert project.universe_ref is not None
    assert project.universe_ref.universe_id == universe.id
    assert project.universe_ref.character_ids == [avatar.id]
    assert project.universe_ref.resolved_characters[0].id == avatar.id
    assert project.universe_ref.resolved_characters[0].bible.model_dump() == avatar.bible.model_dump()


def test_invalid_avatar_id_is_rejected() -> None:
    universe, _, _ = make_universe()

    with pytest.raises(ValueError, match="does not exist"):
        ContentProjectService().create_from_avatar("Unknown", universe, "missing-avatar")


def test_optional_location_context_is_resolved() -> None:
    universe, avatar, location = make_universe()

    project = ContentProjectService().create_from_avatar(
        "Mia enters the hall",
        universe,
        avatar.id,
        location_ids=[location.id],
    )

    assert project.universe_ref is not None
    assert project.universe_ref.location_ids == [location.id]
    assert project.universe_ref.resolved_locations[0].id == location.id


def test_context_resolution_does_not_mutate_universe_and_standalone_projects_remain_valid() -> None:
    universe, avatar, _ = make_universe()
    before = copy.deepcopy(universe.model_dump())

    project = ContentProjectService().create_from_avatar("Mia helps", universe, avatar.id)

    assert universe.model_dump() == before
    standalone = Project(topic="Standalone project")
    assert standalone.universe_ref is None
    assert project.universe_ref is not None
