"""
Tests for the AI Universe domain layer.

Covers:
1. Creating a Universe with characters and locations
2. Creating relationships and events
3. Attaching a Project to a Universe via UniverseContextAgent
4. Resolving Universe context (selective)
5. Project with no Universe remains valid
6. Serialisation / deserialisation (round-trip)
7. No mutable-default-state leakage between instances
"""

from __future__ import annotations

import json

import pytest

from agents.universe_context_agent import UniverseContextAgent
from models.project import Project
from models.universe import (
    Character,
    CharacterBible,
    Location,
    LocationBible,
    Relationship,
    Universe,
    UniverseEvent,
    UniverseReference,
    WorldRule,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────


def make_universe() -> Universe:
    hero = Character(
        name="Aelara",
        role="protagonist",
        bible=CharacterBible(
            appearance="tall, silver hair, glowing eyes",
            personality="brave, curious",
            backstory="Orphaned mage who discovered her powers at age 7",
            abilities=["telekinesis", "light magic"],
        ),
    )
    villain = Character(
        name="Mordax",
        role="antagonist",
        bible=CharacterBible(
            appearance="shadowed figure, red eyes",
            personality="calculating, ruthless",
        ),
    )
    city = Location(
        name="Silverkeep",
        location_type="city",
        bible=LocationBible(
            description="A gleaming magical city on a mountaintop",
            atmosphere="mystical, airy",
        ),
    )
    cave = Location(
        name="The Dark Cavern",
        location_type="dungeon",
        bible=LocationBible(description="An ancient cave beneath Silverkeep"),
    )
    bond = Relationship(
        from_entity_id=hero.id,
        to_entity_id=villain.id,
        relationship_type="enemy",
        description="Aelara and Mordax have been at war for decades",
    )
    home_rel = Relationship(
        from_entity_id=hero.id,
        to_entity_id=city.id,
        relationship_type="home_location",
    )
    past_battle = UniverseEvent(
        title="Battle of Silverkeep",
        description="Mordax besieged the city but was repelled by Aelara",
        involved_entity_ids=[hero.id, villain.id, city.id],
        tags=["battle", "turning_point"],
    )
    magic_rule = WorldRule(
        name="Conservation of Magic",
        description="Every spell cast depletes the caster's life force.",
        category="physics",
        is_hard_constraint=True,
    )
    universe = Universe(
        name="The Aelara Chronicles",
        world_brief="A high-fantasy world where magic and technology coexist.",
        characters=[hero, villain],
        locations=[city, cave],
        relationships=[bond, home_rel],
        events=[past_battle],
        world_rules=[magic_rule],
    )
    return universe


# ── Test 1: Create Universe with characters and locations ──────────────────────


def test_create_universe_with_characters_and_locations():
    u = make_universe()
    assert u.name == "The Aelara Chronicles"
    assert len(u.characters) == 2
    assert len(u.locations) == 2
    assert u.characters[0].name == "Aelara"
    assert u.locations[0].name == "Silverkeep"
    assert u.characters[0].bible.abilities == ["telekinesis", "light magic"]


# ── Test 2: Relationships and events ──────────────────────────────────────────


def test_relationships_and_events():
    u = make_universe()
    hero = u.characters[0]
    villain = u.characters[1]
    city = u.locations[0]

    assert len(u.relationships) == 2
    assert len(u.events) == 1

    rels = u.get_relationships_for(hero.id)
    assert len(rels) == 2

    events = u.get_events_for(city.id)
    assert len(events) == 1
    assert events[0].title == "Battle of Silverkeep"

    # villain has no events with the cave
    cave = u.locations[1]
    assert u.get_events_for(cave.id) == []


# ── Test 3: Attaching a Project to a Universe ──────────────────────────────────


def test_attach_project_to_universe():
    u = make_universe()
    p = Project(topic="Episode 1: The Siege")
    assert p.universe_ref is None

    agent = UniverseContextAgent()
    p2 = agent.run(p, u)

    assert p2.universe_ref is not None
    assert p2.universe_ref.universe_id == u.id
    assert p2.universe_ref.universe_name == "The Aelara Chronicles"
    # Original project is not mutated
    assert p.universe_ref is None


# ── Test 4: Selective Universe context resolution ──────────────────────────────


def test_selective_context_resolution():
    u = make_universe()
    hero = u.characters[0]
    city = u.locations[0]

    p = Project(topic="Episode 2: Return to Silverkeep")
    agent = UniverseContextAgent()
    p2 = agent.run(p, u, character_ids=[hero.id], location_ids=[city.id])

    ref = p2.universe_ref
    assert ref is not None
    assert len(ref.resolved_characters) == 1
    assert ref.resolved_characters[0].id == hero.id
    assert len(ref.resolved_locations) == 1
    assert ref.resolved_locations[0].id == city.id
    # Events involving the hero+city are included
    assert len(ref.resolved_events) == 1
    # World rules are all included by default
    assert len(ref.resolved_rules) == 1
    # Continuity summary mentions the universe name
    assert "Aelara Chronicles" in ref.continuity_summary
    assert "Aelara" in ref.continuity_summary


# ── Test 5: Project with no Universe remains valid ─────────────────────────────


def test_project_without_universe():
    p = Project(topic="Standalone Short Film")
    assert p.universe_ref is None
    # Can still access all other fields normally
    assert p.topic == "Standalone Short Film"
    assert p.generation_jobs == []


# ── Test 6: Serialisation / deserialisation ────────────────────────────────────


def test_universe_round_trip():
    u = make_universe()
    data = u.model_dump()
    u2 = Universe.model_validate(data)
    assert u2.id == u.id
    assert u2.name == u.name
    assert len(u2.characters) == len(u.characters)
    assert u2.characters[0].name == u.characters[0].name
    assert u2.world_rules[0].is_hard_constraint is True


def test_universe_json_round_trip():
    u = make_universe()
    raw = u.model_dump_json()
    u2 = Universe.model_validate_json(raw)
    assert u2.id == u.id
    assert u2.events[0].title == "Battle of Silverkeep"


def test_project_with_universe_ref_round_trip():
    u = make_universe()
    p = Project(topic="Episode 3")
    agent = UniverseContextAgent()
    p2 = agent.run(p, u)

    data = p2.model_dump()
    p3 = Project.model_validate(data)
    assert p3.universe_ref is not None
    assert p3.universe_ref.universe_id == u.id
    assert len(p3.universe_ref.resolved_characters) == 2


# ── Test 7: No mutable-default-state leakage ──────────────────────────────────


def test_no_mutable_default_leakage_characters():
    c1 = Character(name="Alpha")
    c2 = Character(name="Beta")
    c1.bible.abilities.append("flying")
    # c2 must not be affected
    assert c2.bible.abilities == []


def test_no_mutable_default_leakage_universe():
    u1 = Universe(name="World A")
    u2 = Universe(name="World B")
    u1.characters.append(Character(name="Ghost"))
    assert len(u2.characters) == 0


def test_no_mutable_default_leakage_universe_ref():
    r1 = UniverseReference(universe_id="u1")
    r2 = UniverseReference(universe_id="u2")
    r1.character_ids.append("c1")
    assert r2.character_ids == []


def test_no_mutable_default_leakage_project():
    p1 = Project(topic="P1")
    p2 = Project(topic="P2")
    from models.project import GenerationJob
    p1.generation_jobs.append(
        GenerationJob(
            scene_number=1,
            provider="seedance",
            priority="high",
            image_prompt="x",
            video_prompt="y",
            estimated_seconds=60,
            estimated_cost=0.1,
            parallel_group=1,
        )
    )
    assert len(p2.generation_jobs) == 0


# ── Test: Universe lookup helpers ──────────────────────────────────────────────


def test_universe_get_character():
    u = make_universe()
    hero = u.characters[0]
    found = u.get_character(hero.id)
    assert found is not None
    assert found.name == "Aelara"
    assert u.get_character("nonexistent") is None


def test_universe_get_location():
    u = make_universe()
    city = u.locations[0]
    found = u.get_location(city.id)
    assert found is not None
    assert found.name == "Silverkeep"
    assert u.get_location("nonexistent") is None


def test_world_rule_hard_constraint():
    rule = WorldRule(
        name="No Time Travel",
        description="Time travel is impossible",
        is_hard_constraint=True,
    )
    assert rule.is_hard_constraint is True
    soft = WorldRule(name="Gravity", description="Things fall down")
    assert soft.is_hard_constraint is False
