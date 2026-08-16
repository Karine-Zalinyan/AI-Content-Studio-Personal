"""Focused tests for the current StoryboardContext → GenerationPlanner boundary."""

from models.generation_plan import GenerationPlan
from models.storyboard import StoryboardContext, StoryboardShot
from services.generation_planner_service import GenerationPlanner


def make_storyboard() -> StoryboardContext:
    return StoryboardContext(
        project_topic="Mia helps a friend",
        universe_id="universe-1",
        character_ids=["avatar-1"],
        location_ids=["location-1"],
        shots=[
            StoryboardShot(
                scene_number=2,
                duration=3,
                goal="Help",
                visual="Mia opens the door",
                characters=["avatar-1"],
                locations=["location-1"],
                camera={"shot": "close-up", "movement": "push-in"},
                image_prompt="Mia opens the door",
                video_prompt="Mia opens the door gently",
            ),
            StoryboardShot(
                scene_number=1,
                duration=2,
                goal="Arrive",
                characters=["avatar-1"],
                locations=["location-1"],
                video_prompt="Mia arrives",
            ),
        ],
    )


def test_plans_shots_in_deterministic_scene_order() -> None:
    plan = GenerationPlanner().create(make_storyboard())

    assert isinstance(plan, GenerationPlan)
    assert [job.scene_number for job in plan.jobs] == [1, 2]
    assert [job.sequence for job in plan.jobs] == [1, 2]
    assert plan.jobs[1].camera == {"shot": "close-up", "movement": "push-in"}
    assert plan.jobs[1].duration == 3


def test_preserves_canonical_character_and_location_identity() -> None:
    plan = GenerationPlanner().create(make_storyboard())

    for job in plan.jobs:
        assert job.character_ids == ["avatar-1"]
        assert job.location_ids == ["location-1"]
    assert plan.universe_id == "universe-1"


def test_repeated_planning_is_deterministic() -> None:
    storyboard = make_storyboard()

    first = GenerationPlanner().create(storyboard)
    second = GenerationPlanner().create(storyboard)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_empty_storyboard_produces_empty_plan() -> None:
    plan = GenerationPlanner().create(StoryboardContext(project_topic="Empty"))

    assert plan.project_topic == "Empty"
    assert plan.jobs == []


def test_planner_does_not_mutate_storyboard() -> None:
    storyboard = make_storyboard()
    before = storyboard.model_dump(mode="json")

    GenerationPlanner().create(storyboard)

    assert storyboard.model_dump(mode="json") == before
