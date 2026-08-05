"""
Shared Pydantic data models for the AI Content Studio project workflow.

These models represent the data structures flowing through agents:
Idea → DirectorPlan → Assets → Voice → Video → Export
"""

from __future__ import annotations

from typing import Optional

from models.base import AppBaseModel


# ── Idea models ───────────────────────────────────────────────────────────────


class Idea(AppBaseModel):
    """Generated video concept from IdeaAgent."""

    title: str
    hook: str
    core_story: str
    emotion: str
    thumbnail: str
    viral_score: int


# ── Director models ───────────────────────────────────────────────────────────


class Camera(AppBaseModel):
    """Structured camera specification."""

    shot: str  # e.g. "wide", "medium", "close-up"
    movement: str  # e.g. "static", "dolly-in", "tracking"
    angle: str  # e.g. "eye-level", "high", "low"


class Lighting(AppBaseModel):
    """Structured lighting specification."""

    type: str  # e.g. "key", "fill", "rim", "ambient"
    temperature: str  # e.g. "cool", "warm", "neutral"


class Music(AppBaseModel):
    """Structured music specification."""

    genre: str  # e.g. "ambient", "orchestral", "electronic"
    intensity: str  # e.g. "minimal", "subtle", "moderate", "intense"


class Scene(AppBaseModel):
    """Single scene in a director plan."""

    scene: int
    duration: int  # seconds
    goal: str
    visual: str
    camera: Camera
    lighting: Lighting
    emotion: str
    voiceover: str
    music: Music
    sfx: list[str]
    transition: str
    image_prompt: str
    video_prompt: str


class DirectorPlan(AppBaseModel):
    """Scene breakdown from DirectorAgent."""

    duration: int  # total seconds
    style: str
    aspect_ratio: str  # e.g. "9:16"
    fps: int
    scenes: list[Scene]


# ── Asset models ──────────────────────────────────────────────────────────────


class AssetSet(AppBaseModel):
    """Generated visual assets for a project."""

    images: list[str] = []  # file paths to generated images per scene
    videos: list[str] = []  # file paths to generated video clips per scene
    metadata: dict = {}  # arbitrary metadata


# ── Voice models ──────────────────────────────────────────────────────────────


class VoiceTrack(AppBaseModel):
    """Generated voiceover for a project."""

    audio_file: Optional[str] = None  # file path to voiceover
    language: str = "en"
    voice_id: Optional[str] = None  # identifier for the voice used
    metadata: dict = {}  # arbitrary metadata


# ── Video models ──────────────────────────────────────────────────────────────


class VideoOutput(AppBaseModel):
    """Assembled video output."""

    file_path: Optional[str] = None  # final video file
    duration: int = 0  # seconds
    resolution: str = "1080p"
    format: str = "mp4"
    metadata: dict = {}  # arbitrary metadata


# ── Export models ─────────────────────────────────────────────────────────────


class ExportSettings(AppBaseModel):
    """Final export configuration."""

    title: str = ""
    description: str = ""
    tags: list[str] = []
    thumbnail_file: Optional[str] = None
    metadata: dict = {}


# ── Project root model ────────────────────────────────────────────────────────


class Project(AppBaseModel):
    """Top-level project containing all workflow stages."""

    topic: str
    idea: Optional[Idea] = None
    director: Optional[DirectorPlan] = None
    assets: AssetSet = AssetSet()
    voice: VoiceTrack = VoiceTrack()
    video: VideoOutput = VideoOutput()
    export: ExportSettings = ExportSettings()
