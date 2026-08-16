"""Provider-neutral generation plan models for the Social Content Studio MVP."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from models.base import AppBaseModel


class GenerationJob(AppBaseModel):
    """Deterministic, provider-neutral specification for one storyboard shot."""

    job_id: str
    shot_id: str
    scene_number: int
    sequence: int
    prompt: str = ""
    negative_constraints: list[str] = Field(default_factory=list)
    duration: int = 0
    aspect_ratio: str = "9:16"
    media_type: str = "video"
    character_ids: list[str] = Field(default_factory=list)
    location_ids: list[str] = Field(default_factory=list)
    character_bibles: list[dict[str, Any]] = Field(default_factory=list)
    location_bibles: list[dict[str, Any]] = Field(default_factory=list)
    camera: dict[str, Any] = Field(default_factory=dict)
    image_prompt: str = ""
    video_prompt: str = ""


class GenerationPlan(AppBaseModel):
    """Ordered generation jobs derived from one storyboard context."""

    project_topic: str
    universe_id: str | None = None
    jobs: list[GenerationJob] = Field(default_factory=list)
