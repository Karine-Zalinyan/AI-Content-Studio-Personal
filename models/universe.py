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


def _new_id() -> str:
    """Generate a new stable UUID string."""
    return str(uuid.uuid4())


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


class CharacterBible(AppBaseModel):
    """Canonical character description and traits for continuity."""

    appearance: str = ""
    personality: str = ""
    backstory: str = ""
    speech_patterns: str = ""
    abilities: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    visual_reference: str = ""
    visual_reference_metadata: dict = Field(default_factory=dict)
    generation_description: str = ""
    extra: dict = Field(default_factory=dict)


class Character(AppBaseModel):
    """Persistent AI Avatar / character entity in a Universe."""

    id: str = Field(default_factory=_new_id)
    name: str
    aliases: list[str] = Field(default_factory=list)
    role: str = ""
    bible: CharacterBible = Field(default_factory=CharacterBible)
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


# User-facing name for the canonical Character domain model. This is an alias,
# not a second character system, so Universe.characters remains the source of truth.
Avatar = Character


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
    location_type: str = ""
    bible: LocationBible = Field(default_factory=LocationBible)
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


class Relationship(AppBaseModel):
    """Directed relationship between any two Universe entities (characters or locations)."""

    id: str = Field(default_factory=_new_id)
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    description: str = ""
    strength: float = 1.0
    created_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


class UniverseEvent(AppBaseModel):
    """A canonically important event in the Universe's history."""

    id: str = Field(default_factory=_new_id)
    title: str
    description: str = ""
    in_universe_timestamp: Optional[str] = None
    real_created_at: str = Field(default_factory=_utcnow)
    involved_entity_ids: list[str] = Field(default_factory=list)
    source_project_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class WorldRule(AppBaseModel):
    """A persistent, canonical rule that governs the Universe."""

    id: str = Field(default_factory=_new_id)
    name: str
    description: str
    category: str = ""
    is_hard_constraint: bool = False
    created_at: str = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


class Universe(AppBaseModel):
    """Top-level persistent world container."""

    id: str = Field(default_factory=_new_id)
    name: str
    description: str = ""
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


class UniverseReference(AppBaseModel):
    """Lightweight reference from a Project/Episode to a Universe."""

    universe_id: str
    universe_name: str = ""
    character_ids: list[str] = Field(default_factory=list)
    location_ids: list[str] = Field(default_factory=list)
    continuity_summary: str = ""
    resolved_characters: list[Character] = Field(default_factory=list)
    resolved_locations: list[Location] = Field(default_factory=list)
    resolved_relationships: list[Relationship] = Field(default_factory=list)
    resolved_events: list[UniverseEvent] = Field(default_factory=list)
    resolved_rules: list[WorldRule] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
