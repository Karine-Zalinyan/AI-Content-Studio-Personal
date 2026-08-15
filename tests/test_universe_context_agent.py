"""
Edge-case tests for UniverseContextAgent.

Covers:
- unknown / nonexistent character and location IDs
- max_events=0 and max_events with a negative-like boundary (clamped to 0)
- event ordering (newest first)
- empty Universe (no characters, locations, events)
- include_all_rules=False
"""

from __future__ import annotations

import pytest

from agents.universe_context_agent import UniverseContextAgent
from models.project import Project
from models.universe import Character, Location, Universe, UniverseEvent, WorldRule


# ── helpers ────────────────────────────────────────────────────────────────────


def _char(name: str) -> Character:
    return Character(name=name, role="supporting")


def _loc(name: str) -> Location:
    return Location(name=name)


def _event(title: str, entity_ids: list[str], created_at: str) -> UniverseEvent:
    """Create a UniverseEvent with a fixed real_created_at for deterministic ordering tests."""
    e = UniverseEvent(title=title, involved_entity_ids=entity_ids)
    object.__setattr__(e, "real_created_at", created_at)
    return e


def _project() -> Project:
    return Project(topic="Test Episode")


def _agent() -> UniverseContextAgent:
    return UniverseContextAgent()


# ── Test: unknown character / location IDs are silently ignored ────────────────


def test_unknown_character_ids_ignored():
    hero = _char("Hero")
    u = Universe(name="Test World", characters=[hero])
    p = _project()

    ref = _agent().run(p, u, character_ids=["nonexistent-id-1", "nonexistent-id-2"]).universe_ref
    assert ref is not None
    assert ref.resolved_characters == []
    assert ref.character_ids == []


def test_unknown_location_ids_ignored():
    city = _loc("City")
    u = Universe(name="Test World", locations=[city])
    p = _project()

    ref = _agent().run(p, u, location_ids=["bad-id"]).universe_ref
    assert ref is not None
    assert ref.resolved_locations == []
    assert ref.location_ids == []


def test_mix_of_valid_and_unknown_ids():
    hero = _char("Hero")
    villain = _char("Villain")
    u = Universe(name="Test World", characters=[hero, villain])
    p = _project()

    ref = _agent().run(p, u, character_ids=[hero.id, "nonexistent"]).universe_ref
    assert ref is not None
    assert len(ref.resolved_characters) == 1
    assert ref.resolved_characters[0].id == hero.id


# ── Test: max_events boundary values ──────────────────────────────────────────


def test_max_events_zero_returns_no_events():
    hero = _char("Hero")
    u = Universe(
        name="World",
        characters=[hero],
        events=[
            UniverseEvent(title="Event A", involved_entity_ids=[hero.id]),
            UniverseEvent(title="Event B", involved_entity_ids=[hero.id]),
        ],
    )
    p = _project()

    ref = _agent().run(p, u, max_events=0).universe_ref
    assert ref is not None
    assert ref.resolved_events == []


def test_max_events_one_returns_single_event():
    hero = _char("Hero")
    e1 = UniverseEvent(title="First", involved_entity_ids=[hero.id])
    e2 = UniverseEvent(title="Second", involved_entity_ids=[hero.id])
    u = Universe(name="World", characters=[hero], events=[e1, e2])
    p = _project()

    ref = _agent().run(p, u, max_events=1).universe_ref
    assert ref is not None
    assert len(ref.resolved_events) == 1


def test_max_events_larger_than_available_returns_all():
    hero = _char("Hero")
    events = [UniverseEvent(title=f"Ev{i}", involved_entity_ids=[hero.id]) for i in range(3)]
    u = Universe(name="World", characters=[hero], events=events)
    p = _project()

    ref = _agent().run(p, u, max_events=100).universe_ref
    assert ref is not None
    assert len(ref.resolved_events) == 3


# ── Test: event ordering (newest first) ───────────────────────────────────────


def test_events_ordered_newest_first():
    hero = _char("Hero")

    e_old = _event("Old Battle", [hero.id], "2020-01-01T00:00:00+00:00")
    e_mid = _event("Mid Treaty", [hero.id], "2022-06-15T12:00:00+00:00")
    e_new = _event("New War", [hero.id], "2024-12-31T23:59:59+00:00")

    # Intentionally insert in non-chronological order
    u = Universe(name="World", characters=[hero], events=[e_mid, e_old, e_new])
    p = _project()

    ref = _agent().run(p, u).universe_ref
    assert ref is not None
    titles = [e.title for e in ref.resolved_events]
    assert titles == ["New War", "Mid Treaty", "Old Battle"]


def test_events_with_max_events_takes_newest():
    hero = _char("Hero")

    e_old = _event("Ancient", [hero.id], "2010-01-01T00:00:00+00:00")
    e_new = _event("Recent", [hero.id], "2025-01-01T00:00:00+00:00")

    u = Universe(name="World", characters=[hero], events=[e_old, e_new])
    p = _project()

    ref = _agent().run(p, u, max_events=1).universe_ref
    assert ref is not None
    assert len(ref.resolved_events) == 1
    assert ref.resolved_events[0].title == "Recent"


# ── Test: empty Universe ────────────────────────────────────────────────────────


def test_empty_universe_produces_valid_ref():
    u = Universe(name="Void")
    p = _project()

    ref = _agent().run(p, u).universe_ref
    assert ref is not None
    assert ref.universe_id == u.id
    assert ref.resolved_characters == []
    assert ref.resolved_locations == []
    assert ref.resolved_events == []
    assert ref.resolved_rules == []
    assert "Void" in ref.continuity_summary


def test_empty_universe_with_explicit_ids():
    u = Universe(name="Void")
    p = _project()

    ref = _agent().run(p, u, character_ids=["c1"], location_ids=["l1"]).universe_ref
    assert ref is not None
    assert ref.resolved_characters == []
    assert ref.resolved_locations == []


# ── Test: include_all_rules=False suppresses world rules ──────────────────────


def test_include_all_rules_false():
    rule = WorldRule(name="No Magic", description="Magic is banned")
    u = Universe(name="Dystopia", world_rules=[rule])
    p = _project()

    ref = _agent().run(p, u, include_all_rules=False).universe_ref
    assert ref is not None
    assert ref.resolved_rules == []


def test_include_all_rules_true_default():
    rule = WorldRule(name="No Magic", description="Magic is banned")
    u = Universe(name="Dystopia", world_rules=[rule])
    p = _project()

    ref = _agent().run(p, u).universe_ref
    assert ref is not None
    assert len(ref.resolved_rules) == 1
    assert ref.resolved_rules[0].name == "No Magic"


# ── Test: events not involving selected entities are excluded ──────────────────


def test_events_for_unselected_entities_excluded():
    hero = _char("Hero")
    bystander = _char("Bystander")
    hero_event = UniverseEvent(title="Hero's Story", involved_entity_ids=[hero.id])
    bystander_event = UniverseEvent(title="Bystander's Story", involved_entity_ids=[bystander.id])

    u = Universe(name="World", characters=[hero, bystander], events=[hero_event, bystander_event])
    p = _project()

    # Request only hero's context
    ref = _agent().run(p, u, character_ids=[hero.id]).universe_ref
    assert ref is not None
    titles = [e.title for e in ref.resolved_events]
    assert "Hero's Story" in titles
    assert "Bystander's Story" not in titles


# ── Test: original project is never mutated ───────────────────────────────────


def test_original_project_not_mutated():
    u = Universe(name="World", characters=[_char("Alpha")])
    p = Project(topic="Original")
    assert p.universe_ref is None

    _agent().run(p, u)
    assert p.universe_ref is None


# ── Test: continuity summary content ─────────────────────────────────────────


def test_continuity_summary_includes_hard_rules():
    rule = WorldRule(name="No Resurrection", description="Dead stays dead", is_hard_constraint=True)
    u = Universe(name="Grim World", world_rules=[rule])
    p = _project()

    ref = _agent().run(p, u).universe_ref
    assert ref is not None
    assert "No Resurrection" in ref.continuity_summary


def test_continuity_summary_no_hard_rules_not_mentioned():
    rule = WorldRule(name="Soft Guideline", description="Just a hint", is_hard_constraint=False)
    u = Universe(name="Soft World", world_rules=[rule])
    p = _project()

    ref = _agent().run(p, u).universe_ref
    assert ref is not None
    # Soft rules do not appear in the "Hard world rules:" line
    assert "Hard world rules" not in ref.continuity_summary
