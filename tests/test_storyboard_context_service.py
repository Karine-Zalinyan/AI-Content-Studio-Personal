"""Focused tests for the Project → Storyboard application boundary."""

import copy

import pytest

from models.project import Project, TimelineScene
from models.universe import Avatar, CharacterBible, Location, LocationBible, Universe
from services.content_project_service import ContentProjectService
from services.storyboard_context_service import StoryboardContextService


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


def test_universe_project_resolves_canonical_avatar_and_location() -> None:
    universe, avatar, location = make_universe()
    project = ContentProjectService().create_from_avatar(
        "Mia helps a friend", universe, avatar.id, location_ids=[location.id]
    )
    project.timeline = [
        TimelineScene(
            scene_number=2,
            duration=3,
            goal="Help",
            visual="Mia opens the door",
            characters=[avatar.id],
            image_prompt="Mia opens the door",
            video_prompt="Mia opens the door gently",
        ),
        TimelineScene(scene_number=1, duration=2, goal="Arrive"),
    ]
    before = copy.deepcopy(universe.model_dump())

    context = StoryboardContextService().create(project, universe)

    assert context.universe_id == universe.id
    assert context.character_ids == [avatar.id]
    assert context.location_ids == [location.id]
    assert context.resolved_characters[0].id == avatar.id
    assert context.resolved_characters[0].bible.model_dump() == avatar.bible.model_dump()
    assert context.resolved_locations[0].id == location.id
    assert [shot.scene_number for shot in context.shots] == [1, 2]
    assert context.shots[1].characters == [avatar.id]
    assert universe.model_dump() == before


def test_missing_universe_reference_is_clear_and_empty() -> None:
    project = Project(topic="Standalone project")

    context = StoryboardContextService().create(project)

    assert context.universe_id is None
    assert context.character_ids == []
    assert context.location_ids == []
    assert context.resolved_characters == []
    assert context.resolved_locations == []
    assert len(context.shots) == 1
    assert context.shots[0].goal == project.topic


def test_universe_reference_requires_matching_universe() -> None:
    universe, avatar, _ = make_universe()
    project = ContentProjectService().create_from_avatar("Mia helps", universe, avatar.id)
    other_universe = Universe(name="Other Universe")

    with pytest.raises(ValueError, match="does not match"):
        StoryboardContextService().create(project, other_universe)


def test_unknown_canonical_entities_are_rejected() -> None:
    universe, avatar, _ = make_universe()
    project = ContentProjectService().create_from_avatar("Mia helps", universe, avatar.id)
    assert project.universe_ref is not None
    project.universe_ref.character_ids = ["missing-character"]

    with pytest.raises(ValueError, match="Unknown character IDs"):
        StoryboardContextService().create(project, universe)
