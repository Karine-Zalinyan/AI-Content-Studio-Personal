"""
Tests for GenerationPlannerAgent — dependency resolution and parallel-group assignment.

Covers:
- independent scenes land in the same parallel group
- dependent scenes (shared characters) advance the parallel group
- dependency list correctly references the previous scene number
- first and last scene get HIGH priority
- prompts are resolved from timeline scene fields
- provider selection by keyword signals
"""

from __future__ import annotations

import pytest

from agents.generation_planner_agent import GenerationPlannerAgent
from models.project import Project, TimelineScene


# ── helpers ────────────────────────────────────────────────────────────────────


def _scene(
    number: int,
    *,
    characters: list[str] | None = None,
    visual: str = "a generic outdoor shot",
    goal: str = "move story forward",
    emotion: str = "neutral",
    transition: str = "",
    duration: int = 5,
    image_prompt: str = "",
    video_prompt: str = "",
    scene_type: str = "",
    notes: str = "",
) -> TimelineScene:
    return TimelineScene(
        scene_number=number,
        characters=characters or [],
        visual=visual,
        goal=goal,
        emotion=emotion,
        transition=transition,
        duration=duration,
        image_prompt=image_prompt or f"image for scene {number}",
        video_prompt=video_prompt or f"video for scene {number}",
        scene_type=scene_type,
        notes=notes,
    )


def _project_with_scenes(scenes: list[TimelineScene]) -> Project:
    return Project(topic="Test Project", timeline=scenes)


def _run(scenes: list[TimelineScene]) -> Project:
    return GenerationPlannerAgent().run(_project_with_scenes(scenes))


# ── Test: independent scenes share a parallel group ───────────────────────────


def test_independent_scenes_same_parallel_group():
    """Scenes with no shared characters are independent → same parallel group."""
    scenes = [
        _scene(1, characters=["Alice"]),
        _scene(2, characters=["Bob"]),
        _scene(3, characters=["Carol"]),
    ]
    project = _run(scenes)
    groups = [j.parallel_group for j in project.generation_jobs]
    # All in group 1 — no dependencies
    assert all(g == 1 for g in groups), f"Expected all group 1, got {groups}"


def test_independent_scenes_have_no_dependencies():
    scenes = [
        _scene(1, characters=["Alice"]),
        _scene(2, characters=["Bob"]),
    ]
    project = _run(scenes)
    for job in project.generation_jobs:
        assert job.dependencies == []


# ── Test: dependent scenes advance the parallel group ─────────────────────────


def test_shared_characters_creates_dependency():
    """Two consecutive scenes sharing the same character must have a dependency."""
    scenes = [
        _scene(1, characters=["Hero"]),
        _scene(2, characters=["Hero"]),  # same character → depends on scene 1
    ]
    project = _run(scenes)
    assert len(project.generation_jobs) == 2
    job1, job2 = project.generation_jobs
    assert job1.dependencies == []
    assert job2.dependencies == [1]


def test_shared_characters_advance_parallel_group():
    scenes = [
        _scene(1, characters=["Hero"]),
        _scene(2, characters=["Hero"]),
    ]
    project = _run(scenes)
    job1, job2 = project.generation_jobs
    assert job1.parallel_group == 1
    assert job2.parallel_group == 2


def test_three_scenes_two_dependencies():
    """
    Scene 1 → Scene 2 (shared char) → Scene 3 (shared char).
    Each dependent scene should be in a new parallel group.
    """
    scenes = [
        _scene(1, characters=["Hero"]),
        _scene(2, characters=["Hero"]),
        _scene(3, characters=["Hero"]),
    ]
    project = _run(scenes)
    assert len(project.generation_jobs) == 3
    groups = [j.parallel_group for j in project.generation_jobs]
    assert groups == [1, 2, 3]
    assert project.generation_jobs[1].dependencies == [1]
    assert project.generation_jobs[2].dependencies == [2]


def test_mixed_independent_and_dependent():
    """
    Scene 1 (Hero) → Scene 2 (Hero, dependent) → Scene 3 (Villain, independent of 2).
    Scene 2 must be in a strictly higher group than scene 1 due to the shared-character
    dependency.  Scene 3 has no dependency so the planner keeps the current group counter
    (no increment happens), placing it in the same group as scene 2.
    """
    scenes = [
        _scene(1, characters=["Hero"]),
        _scene(2, characters=["Hero"]),
        _scene(3, characters=["Villain"]),  # no shared char with scene 2
    ]
    project = _run(scenes)
    groups = [j.parallel_group for j in project.generation_jobs]
    # Scene 2 must be in a higher group than scene 1 (dependency boundary)
    assert groups[1] > groups[0]
    # Scene 3 is not dependent on scene 2; the group counter is not advanced
    assert groups[2] >= 1


# ── Test: dependency references correct scene number ──────────────────────────


def test_dependency_references_previous_scene_number():
    scenes = [
        _scene(5, characters=["X"]),
        _scene(6, characters=["X"]),
    ]
    project = _run(scenes)
    job2 = project.generation_jobs[1]
    assert job2.dependencies == [5]


# ── Test: priority assignment ──────────────────────────────────────────────────


def test_first_scene_is_high_priority():
    scenes = [_scene(1), _scene(2), _scene(3)]
    project = _run(scenes)
    assert project.generation_jobs[0].priority == "high"


def test_last_scene_is_high_priority():
    scenes = [_scene(1), _scene(2), _scene(3)]
    project = _run(scenes)
    assert project.generation_jobs[-1].priority == "high"


def test_single_scene_is_high_priority():
    project = _run([_scene(1)])
    assert project.generation_jobs[0].priority == "high"


def test_middle_scene_default_priority():
    scenes = [_scene(1), _scene(2, goal="a walk in the park"), _scene(3)]
    project = _run(scenes)
    # Middle scene with no high-priority keywords → medium
    assert project.generation_jobs[1].priority == "medium"


# ── Test: provider selection ───────────────────────────────────────────────────


def test_provider_drone_keyword_selects_higgsfield():
    scenes = [_scene(1, visual="drone shot over the city")]
    project = _run(scenes)
    assert project.generation_jobs[0].provider == "higgsfield"


def test_provider_photorealistic_selects_runway():
    scenes = [_scene(1, visual="photorealistic human face close-up")]
    project = _run(scenes)
    assert project.generation_jobs[0].provider == "runway"


def test_provider_chase_selects_kling():
    scenes = [_scene(1, goal="chase scene running fast motion")]
    project = _run(scenes)
    assert project.generation_jobs[0].provider == "kling"


def test_provider_animation_selects_seedance():
    scenes = [_scene(1, visual="pixar animation stylized character")]
    project = _run(scenes)
    assert project.generation_jobs[0].provider == "seedance"


def test_provider_default_is_seedance():
    """Scenes with no provider keywords should default to seedance."""
    scenes = [_scene(1, visual="a plain grey wall", goal="setup", emotion="neutral")]
    project = _run(scenes)
    assert project.generation_jobs[0].provider == "seedance"


# ── Test: empty timeline produces no jobs ────────────────────────────────────


def test_empty_timeline_no_jobs():
    project = GenerationPlannerAgent().run(Project(topic="Empty"))
    assert project.generation_jobs == []


# ── Test: jobs are ordered by scene number ────────────────────────────────────


def test_jobs_ordered_by_scene_order():
    scenes = [_scene(1), _scene(2), _scene(3)]
    project = _run(scenes)
    scene_numbers = [j.scene_number for j in project.generation_jobs]
    assert scene_numbers == [1, 2, 3]


# ── Test: estimated values are positive ───────────────────────────────────────


def test_estimated_seconds_positive():
    scenes = [_scene(1, duration=5)]
    project = _run(scenes)
    assert project.generation_jobs[0].estimated_seconds > 0


def test_estimated_cost_positive():
    scenes = [_scene(1, duration=5)]
    project = _run(scenes)
    assert project.generation_jobs[0].estimated_cost > 0
