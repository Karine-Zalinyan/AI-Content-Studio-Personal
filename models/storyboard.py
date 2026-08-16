"""Models for the deterministic Project → Storyboard application boundary."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from models.base import AppBaseModel
from models.universe import Character, Location


class StoryboardShot(AppBaseModel):
    """Minimal shot-plan unit ready for a later generation planner."""

    scene_number: int
    duration: int = 0
    goal: str = ""
    visual: str = ""
    emotion: str = ""
    transition: str = ""
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    camera: dict[str, Any] = Field(default_factory=dict)
    image_prompt: str = ""
    video_prompt: str = ""


class StoryboardContext(AppBaseModel):
    """Resolved, immutable-in-practice context for storyboard generation."""

    project_topic: str
    universe_id: str | None = None
    character_ids: list[str] = Field(default_factory=list)
    location_ids: list[str] = Field(default_factory=list)
    resolved_characters: list[Character] = Field(default_factory=list)
    resolved_locations: list[Location] = Field(default_factory=list)
    shots: list[StoryboardShot] = Field(default_factory=list)
