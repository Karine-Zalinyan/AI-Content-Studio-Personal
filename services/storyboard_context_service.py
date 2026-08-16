"""Application-layer bridge from Universe-aware Projects to storyboard context."""

from __future__ import annotations

from models.project import Project
from models.storyboard import StoryboardContext, StoryboardShot
from models.universe import Universe


class StoryboardContextService:
    """Build a deterministic storyboard context without mutating domain models."""

    def create(self, project: Project, universe: Universe | None = None) -> StoryboardContext:
        """Resolve only the entities explicitly referenced by ``project``.

        A standalone Project produces a clear empty Universe context but still
        gets a minimal shot from its topic so it remains executable by the
        downstream generation planner. If a Universe is supplied, its identity
        must match the Project reference; no implicit characters or locations
        are invented.
        """
        reference = project.universe_ref
        if reference is None:
            shots = [StoryboardShot(scene_number=1, goal=project.topic)] if project.topic else []
            return StoryboardContext(project_topic=project.topic, shots=shots)

        if universe is None:
            raise ValueError("Universe is required for a Universe-aware Project.")
        if universe.id != reference.universe_id:
            raise ValueError(
                f"Universe '{universe.id}' does not match Project reference '{reference.universe_id}'."
            )

        characters = [
            character
            for character_id in reference.character_ids
            if (character := universe.get_character(character_id)) is not None
        ]
        locations = [
            location
            for location_id in reference.location_ids
            if (location := universe.get_location(location_id)) is not None
        ]

        missing_characters = set(reference.character_ids) - {c.id for c in characters}
        missing_locations = set(reference.location_ids) - {loc.id for loc in locations}
        if missing_characters:
            raise ValueError(f"Unknown character IDs in Project reference: {sorted(missing_characters)}")
        if missing_locations:
            raise ValueError(f"Unknown location IDs in Project reference: {sorted(missing_locations)}")

        shots = [
            StoryboardShot(
                scene_number=scene.scene_number,
                duration=scene.duration,
                goal=scene.goal,
                visual=scene.visual,
                emotion=scene.emotion,
                transition=scene.transition,
                characters=list(scene.characters),
                camera=dict(scene.camera),
                image_prompt=scene.image_prompt,
                video_prompt=scene.video_prompt,
            )
            for scene in sorted(project.timeline, key=lambda item: item.scene_number)
        ]

        if not shots and project.topic:
            shots = [StoryboardShot(scene_number=1, goal=project.topic)]

        # Preserve canonical reference order and do not mutate Project/Universe.
        return StoryboardContext(
            project_topic=project.topic,
            universe_id=reference.universe_id,
            character_ids=list(reference.character_ids),
            location_ids=list(reference.location_ids),
            resolved_characters=characters,
            resolved_locations=locations,
            shots=shots,
        )
