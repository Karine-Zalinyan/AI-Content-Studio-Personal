"""Application-layer bridge from StoryboardContext to generation jobs."""

from __future__ import annotations

import hashlib
import json

from models.generation_plan import GenerationJob, GenerationPlan
from models.storyboard import StoryboardContext, StoryboardShot


class GenerationPlanner:
    """Create a deterministic provider-neutral generation plan without side effects."""

    def create(self, storyboard: StoryboardContext) -> GenerationPlan:
        """Convert each storyboard shot into one traceable generation job."""
        jobs = [self._job_for_shot(storyboard, shot, index) for index, shot in enumerate(
            sorted(storyboard.shots, key=lambda item: item.scene_number), start=1
        )]
        return GenerationPlan(
            project_topic=storyboard.project_topic,
            universe_id=storyboard.universe_id,
            jobs=jobs,
        )

    def _job_for_shot(
        self, storyboard: StoryboardContext, shot: StoryboardShot, sequence: int
    ) -> GenerationJob:
        character_bibles = [
            character.bible.model_dump(mode="json")
            for character_id in shot.characters or storyboard.character_ids
            for character in storyboard.resolved_characters
            if character.id == character_id
        ]
        location_bibles = [
            location.bible.model_dump(mode="json")
            for location_id in shot.locations or storyboard.location_ids
            for location in storyboard.resolved_locations
            if location.id == location_id
        ]
        character_ids = list(shot.characters or storyboard.character_ids)
        location_ids = list(shot.locations or storyboard.location_ids)
        payload = {
            "universe_id": storyboard.universe_id,
            "scene_number": shot.scene_number,
            "sequence": sequence,
            "character_ids": character_ids,
            "location_ids": location_ids,
            "duration": shot.duration,
            "camera": shot.camera,
            "image_prompt": shot.image_prompt,
            "video_prompt": shot.video_prompt,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()[:16]
        prompt = shot.video_prompt or shot.image_prompt or shot.visual or shot.goal
        return GenerationJob(
            job_id=f"gen-{digest}",
            shot_id=f"shot-{shot.scene_number}",
            scene_number=shot.scene_number,
            sequence=sequence,
            prompt=prompt,
            duration=shot.duration,
            character_ids=character_ids,
            location_ids=location_ids,
            character_bibles=character_bibles,
            location_bibles=location_bibles,
            camera=dict(shot.camera),
            image_prompt=shot.image_prompt,
            video_prompt=shot.video_prompt,
        )
