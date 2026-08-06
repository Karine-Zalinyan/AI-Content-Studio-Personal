"""
Shared Pydantic data models for the AI Content Studio project workflow.

These models represent the data structures flowing through agents:
Idea → DirectorPlan → Assets → Voice → Video → Export
"""

from __future__ import annotations

from typing import Any, Literal, Optional

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


# ── Generation planning models ─────────────────────────────────────────────────


class TimelineScene(AppBaseModel):
    """Scene metadata used by generation planning."""

    scene_number: int
    duration: int = 0
    goal: str = ""
    visual: str = ""
    emotion: str = ""
    dialogue: str = ""
    scene_type: str = ""
    characters: list[str] = []
    notes: str = ""
    transition: str = ""
    camera: dict[str, Any] = {}
    image_prompt: str = ""
    video_prompt: str = ""


class GenerationJob(AppBaseModel):
    """Planned generation job for one scene."""

    scene_number: int
    provider: Literal["seedance", "kling", "runway", "higgsfield"]
    priority: Literal["high", "medium", "low"]
    status: Literal["PENDING", "RUNNING", "DONE", "FAILED"] = "PENDING"
    image_prompt: str
    video_prompt: str
    estimated_seconds: int
    estimated_cost: float
    parallel_group: int
    dependencies: list[int] = []
    retry_count: int = 0
    max_retries: int = 3
    notes: str = ""


class GeneratedAsset(AppBaseModel):
    """An AI-generated video asset for a scene."""

    scene_number: int
    provider: str
    file_path: str
    preview_path: str = ""
    duration: float = 0.0
    resolution: str = ""
    generation_time: float = 0.0  # seconds elapsed during generation
    cost: float = 0.0
    metadata: dict[str, Any] = {}


class GenerationLog(AppBaseModel):
    """Execution log entry for one generation job."""

    scene_number: int
    started_at: str
    finished_at: str
    provider: str
    generation_time: float = 0.0
    cost: float = 0.0
    error_message: str = ""


# ── Asset models ──────────────────────────────────────────────────────────────


class AssetSet(AppBaseModel):
    """Generated visual assets for a project."""

    images: list[str] = []  # file paths to generated images per scene
    videos: list[str] = []  # file paths to generated video clips per scene
    ai_videos: list[GeneratedAsset] = []  # AI-generated video assets per scene
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
    stock: dict[str, Any] = {}
    asset_ranking: dict[str, Any] | list[dict[str, Any]] = {}
    prompts: dict[str, Any] = {}
    quality: dict[str, Any] | list[dict[str, Any]] = {}
    assets: AssetSet = AssetSet()
    timeline: list[TimelineScene] = []
    generation_jobs: list[GenerationJob] = []
    generation_logs: list[GenerationLog] = []
    voice: VoiceTrack = VoiceTrack()
    video: VideoOutput = VideoOutput()
    export: ExportSettings = ExportSettings()
