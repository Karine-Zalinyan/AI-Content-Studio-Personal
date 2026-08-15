"""
UniverseContextAgent

Resolves relevant Universe context for a Project and attaches it as a
UniverseReference.  This agent is *read-only* with respect to the Universe –
it selects and snapshots the entities that matter for the current project
rather than mutating the Universe.

Usage
-----
agent = UniverseContextAgent()
project = agent.run(project, universe, character_ids=[...], location_ids=[...])

After running, ``project.universe_ref`` contains a fully resolved snapshot
that downstream agents (DirectorAgent, GenerationPlannerAgent, …) can consume
without importing Universe internals.
"""

from __future__ import annotations

from typing import Optional

from agents.base import BaseAgent
from models.project import Project
from models.universe import (
    Character,
    Location,
    Universe,
    UniverseEvent,
    UniverseReference,
    WorldRule,
)


class UniverseContextAgent(BaseAgent):
    """Resolve and attach Universe context to a Project."""

    def run(  # type: ignore[override]
        self,
        project: Project,
        universe: Universe,
        *,
        character_ids: Optional[list[str]] = None,
        location_ids: Optional[list[str]] = None,
        include_all_rules: bool = True,
        max_events: int = 20,
    ) -> Project:
        """
        Select relevant Universe entities for *project* and attach them.

        Parameters
        ----------
        project:
            The Project that will receive the resolved Universe context.
        universe:
            The source Universe to resolve from.
        character_ids:
            Explicit list of Character IDs relevant to this episode.
            If None, all characters in the Universe are included.
        location_ids:
            Explicit list of Location IDs relevant to this episode.
            If None, all locations in the Universe are included.
        include_all_rules:
            When True (default) all WorldRules are included in the snapshot.
        max_events:
            Maximum number of events to include (most-recent first).

        Returns
        -------
        Project
            A copy of *project* with ``universe_ref`` populated.
        """
        resolved_chars = self._resolve_characters(universe, character_ids)
        resolved_locs = self._resolve_locations(universe, location_ids)
        resolved_events = self._resolve_events(universe, resolved_chars, resolved_locs, max_events)
        resolved_rules: list[WorldRule] = universe.world_rules if include_all_rules else []

        continuity_summary = self._build_continuity_summary(
            universe, resolved_chars, resolved_locs, resolved_events, resolved_rules
        )

        universe_ref = UniverseReference(
            universe_id=universe.id,
            universe_name=universe.name,
            character_ids=[c.id for c in resolved_chars],
            location_ids=[loc.id for loc in resolved_locs],
            continuity_summary=continuity_summary,
            resolved_characters=resolved_chars,
            resolved_locations=resolved_locs,
            resolved_events=resolved_events,
            resolved_rules=resolved_rules,
        )

        return project.model_copy(update={"universe_ref": universe_ref})

    # ── private helpers ────────────────────────────────────────────────────────

    def _resolve_characters(
        self, universe: Universe, character_ids: Optional[list[str]]
    ) -> list[Character]:
        if character_ids is None:
            return list(universe.characters)
        id_set = set(character_ids)
        return [c for c in universe.characters if c.id in id_set]

    def _resolve_locations(
        self, universe: Universe, location_ids: Optional[list[str]]
    ) -> list[Location]:
        if location_ids is None:
            return list(universe.locations)
        id_set = set(location_ids)
        return [loc for loc in universe.locations if loc.id in id_set]

    def _resolve_events(
        self,
        universe: Universe,
        characters: list[Character],
        locations: list[Location],
        max_events: int,
    ) -> list[UniverseEvent]:
        """Return events involving any of the resolved characters or locations, newest first."""
        entity_ids = {c.id for c in characters} | {loc.id for loc in locations}
        relevant = [
            e for e in universe.events
            if any(eid in entity_ids for eid in e.involved_entity_ids)
        ]
        # Sort by real_created_at descending (ISO-8601 strings sort correctly)
        relevant.sort(key=lambda e: e.real_created_at, reverse=True)
        return relevant[:max_events]

    def _build_continuity_summary(
        self,
        universe: Universe,
        characters: list[Character],
        locations: list[Location],
        events: list[UniverseEvent],
        rules: list[WorldRule],
    ) -> str:
        """Build a human-readable continuity summary for injection into prompts."""
        parts: list[str] = [f"Universe: {universe.name}"]
        if universe.world_brief:
            parts.append(f"World brief: {universe.world_brief}")
        if characters:
            char_lines = ", ".join(
                f"{c.name} ({c.role})" if c.role else c.name for c in characters
            )
            parts.append(f"Characters: {char_lines}")
        if locations:
            loc_lines = ", ".join(loc.name for loc in locations)
            parts.append(f"Locations: {loc_lines}")
        if events:
            event_lines = "; ".join(e.title for e in events)
            parts.append(f"Key past events: {event_lines}")
        if rules:
            hard = [r.name for r in rules if r.is_hard_constraint]
            if hard:
                parts.append(f"Hard world rules: {', '.join(hard)}")
        return "\n".join(parts)
