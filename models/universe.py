"""
AI Universe domain models.

Defines the core entities for persistent, interconnected media universes:
Universe → Characters, Locations, Relationships, Events, WorldRules

A Universe is a first-class platform capability that sits above individual
Projects/Episodes and enables continuity, crossovers and persistent world
memory over time.

Projects reference a Universe via UniverseReference; no Universe is required
for a Project to remain valid.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from models.base import AppBaseModel


# ── Helpers ───────────────────────────────────────────────────────────────────


def _new_id() -> str:
    """Generate a new stable UUID string."""
    return str(uuid.uuid4())


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ── Character / CharacterBible ─────────────────────────────────────────────────


class CharacterBible(AppBaseModel):
    """Canonical character description and traits for continuity."""

    appearance: str = ""
    personality: str = ""
    backstory: str = ""
    speech_patterns: str = ""
    abilities: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    # Visual generation reference (e.g. stable-diffusion prompt seed)
    visual_reference: str = ""
    extra: dict = Field(default_factory=dict)


class Character(AppBaseModel):
    """Persistent AI Avatar / character entity in a Universe."""

    id: str = Field(default_factory=_new_id)
    name: str
    aliases: list[str] = Field(default_factory=list)
    role: str = ""  # e.g. "protagonist", "antagonist", "supporting"
    bible: CharacterBible = Field(default_factory=CharacterBible)
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


# ── Location / LocationBible ───────────────────────────────────────────────────


class LocationBible(AppBaseModel):
    """Canonical description of a Universe location."""

    description: str = ""
    atmosphere: str = ""
    visual_style: str = ""
    notable_features: list[str] = Field(default_factory=list)
    visual_reference: str = ""
    extra: dict = Field(default_factory=dict)


class Location(AppBaseModel):
    """Persistent location / setting entity in a Universe."""

    id: str = Field(default_factory=_new_id)
    name: str
    location_type: str = ""  # e.g. "city", "planet", "building", "dimension"
    bible: LocationBible = Field(default_factory=LocationBible)
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


# ── Relationship ───────────────────────────────────────────────────────────────


class Relationship(AppBaseModel):
    """Directed relationship between any two Universe entities (characters or locations)."""

    id: str = Field(default_factory=_new_id)
    # Entity IDs — may refer to Character.id, Location.id, or any future entity
    from_entity_id: str
    to_entity_id: str
    relationship_type: str  # e.g. "ally", "enemy", "family", "lover", "home_location"
    description: str = ""
    strength: float = 1.0  # 0.0 – 1.0 canonical strength / weight
    created_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


# ── UniverseEvent / Memory ─────────────────────────────────────────────────────


class UniverseEvent(AppBaseModel):
    """
    A canonically important event in the Universe's history.

    Events form the persistent memory layer that enables episode continuity:
    later episodes can query which events are relevant to specific characters
    or locations and inject that context into the generation pipeline.
    """

    id: str = Field(default_factory=_new_id)
    title: str
    description: str = ""
    # ISO-8601 in-universe timestamp (can be fictional / relative)
    in_universe_timestamp: Optional[str] = None
    real_created_at: str = Field(default_factory=_utcnow)
    # IDs of characters / locations directly involved
    involved_entity_ids: list[str] = Field(default_factory=list)
    # Which project/episode produced or referenced this event
    source_project_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


# ── WorldRule ──────────────────────────────────────────────────────────────────


class WorldRule(AppBaseModel):
    """
    A persistent, canonical rule that governs the Universe.

    Examples: physical laws, magic systems, societal rules, tone constraints.
    These are surfaced as continuity constraints during generation planning.
    """

    id: str = Field(default_factory=_new_id)
    name: str
    description: str
    category: str = ""  # e.g. "physics", "magic", "society", "tone"
    is_hard_constraint: bool = False  # if True, must never be violated
    created_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


# ── Universe ───────────────────────────────────────────────────────────────────


class Universe(AppBaseModel):
    """
    Top-level persistent world container.

    A Universe owns Characters, Locations, Relationships, Events and WorldRules.
    Multiple Projects/Episodes can reference the same Universe to share
    continuity, canonical entities, and world-level constraints.
    """

    id: str = Field(default_factory=_new_id)
    name: str
    description: str = ""
    # Canonical world-building brief (tone, genre, themes, …)
    world_brief: str = ""
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    events: list[UniverseEvent] = Field(default_factory=list)
    world_rules: list[WorldRule] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)

    # ── lookup helpers ────────────────────────────────────────────────────────

    def get_character(self, character_id: str) -> Optional[Character]:
        """Return the Character with the given ID, or None."""
        for c in self.characters:
            if c.id == character_id:
                return c
        return None

    def get_location(self, location_id: str) -> Optional[Location]:
        """Return the Location with the given ID, or None."""
        for loc in self.locations:
            if loc.id == location_id:
                return loc
        return None

    def get_relationships_for(self, entity_id: str) -> list[Relationship]:
        """Return all Relationships where *entity_id* is either endpoint."""
        return [r for r in self.relationships if entity_id in (r.from_entity_id, r.to_entity_id)]

    def get_events_for(self, entity_id: str) -> list[UniverseEvent]:
        """Return all Events that involve the given entity."""
        return [e for e in self.events if entity_id in e.involved_entity_ids]


# ── UniverseReference ──────────────────────────────────────────────────────────


class UniverseReference(AppBaseModel):
    """
    Lightweight reference from a Project/Episode to a Universe.

    Carries only the IDs that are *relevant* to this episode so that the
    generation pipeline does not receive the entire Universe unnecessarily.
    The UniverseContextAgent is responsible for populating this object.
    """

    universe_id: str
    universe_name: str = ""
    # Subset of character IDs that appear in this project
    character_ids: list[str] = Field(default_factory=list)
    # Subset of location IDs that are relevant
    location_ids: list[str] = Field(default_factory=list)
    # Continuity summary string injected into director/planner prompts
    continuity_summary: str = ""
    # Resolved snapshot – populated by UniverseContextAgent at planning time
    resolved_characters: list[Character] = Field(default_factory=list)
    resolved_locations: list[Location] = Field(default_factory=list)
    # Relationships filtered to those involving the resolved characters/locations
    resolved_relationships: list[Relationship] = Field(default_factory=list)
    resolved_events: list[UniverseEvent] = Field(default_factory=list)
    resolved_rules: list[WorldRule] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
