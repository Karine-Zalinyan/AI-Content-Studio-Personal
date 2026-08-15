"""
GenerationPlannerAgent

Builds a complete generation plan without calling any external providers.
"""

from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from models.project import DirectorPlan, GenerationJob, Project, TimelineScene


class GenerationPlannerAgent(BaseAgent):
    """Plan generation jobs for scenes that need AI asset creation."""

    _provider_profiles = {
        "seedance": {"base_seconds": 45, "seconds_per_scene_second": 8, "cost_per_scene_second": 0.004},
        "kling": {"base_seconds": 60, "seconds_per_scene_second": 7, "cost_per_scene_second": 0.005},
        "runway": {"base_seconds": 75, "seconds_per_scene_second": 9, "cost_per_scene_second": 0.006},
        "higgsfield": {"base_seconds": 90, "seconds_per_scene_second": 10, "cost_per_scene_second": 0.007},
    }

    def run(self, project: Project) -> Project:
        scenes = self._resolve_scenes(project)
        jobs: list[GenerationJob] = []
        current_parallel_group = 1

        for index, scene in enumerate(scenes):
            scene_number = self._scene_number(scene, fallback=index + 1)
            if not self._generation_required(project, scene_number):
                continue

            dependencies = self._dependencies_for_scene(scenes, index)
            if jobs and dependencies:
                current_parallel_group += 1

            image_prompt, video_prompt = self._resolve_prompts(project, scene, scene_number)
            provider = self._select_provider(project, scene, image_prompt, video_prompt)
            priority = self._select_priority(scene, index, len(scenes))
            estimated_seconds = self._estimate_seconds(scene, provider)
            estimated_cost = self._estimate_cost(scene, provider)

            jobs.append(
                GenerationJob(
                    scene_number=scene_number,
                    provider=provider,
                    priority=priority,
                    status="PENDING",
                    image_prompt=image_prompt,
                    video_prompt=video_prompt,
                    estimated_seconds=estimated_seconds,
                    estimated_cost=estimated_cost,
                    parallel_group=current_parallel_group,
                    dependencies=dependencies,
                    retry_count=0,
                    max_retries=3,
                    notes=self._build_notes(scene, provider, priority, dependencies),
                )
            )

        project.generation_jobs = jobs
        return project

    def _resolve_scenes(self, project: Project) -> list[TimelineScene]:
        if project.timeline:
            return project.timeline
        if project.director is None:
            return []

        return [
            TimelineScene(
                scene_number=scene.scene,
                duration=scene.duration,
                goal=scene.goal,
                visual=scene.visual,
                emotion=scene.emotion,
                transition=scene.transition,
                camera=scene.camera.model_dump(),
                image_prompt=scene.image_prompt,
                video_prompt=scene.video_prompt,
            )
            for scene in project.director.scenes
        ]

    @staticmethod
    def _scene_number(scene: TimelineScene, fallback: int) -> int:
        return int(scene.scene_number or fallback)

    def _generation_required(self, project: Project, scene_number: int) -> bool:
        stock_decision = self._stock_decision(project.stock, scene_number)
        ranking = self._scene_data(project.asset_ranking, scene_number)
        selected_stock = stock_decision == "STOCK"
        ranking_quality = self._ranking_quality_confirmed(ranking)
        quality_confirmed = self._quality_agent_confirmed(project.quality, scene_number)
        return not (selected_stock and ranking_quality and quality_confirmed)

    @staticmethod
    def _scene_data(source: dict[str, Any] | list[dict[str, Any]], scene_number: int) -> dict[str, Any]:
        if isinstance(source, dict):
            direct_value = source.get(str(scene_number), source.get(scene_number))
            if isinstance(direct_value, dict):
                return direct_value

            for key in ("by_scene", "scenes", "items", "results"):
                nested = source.get(key)
                if isinstance(nested, dict):
                    value = nested.get(str(scene_number), nested.get(scene_number))
                    if isinstance(value, dict):
                        return value
                if isinstance(nested, list):
                    for item in nested:
                        if isinstance(item, dict) and str(item.get("scene_number", item.get("scene"))) == str(
                            scene_number
                        ):
                            return item
            return source if any(k in source for k in ("selected_asset", "quality", "approved")) else {}

        if isinstance(source, list):
            for item in source:
                if isinstance(item, dict) and str(item.get("scene_number", item.get("scene"))) == str(scene_number):
                    return item
        return {}

    @staticmethod
    def _stock_decision(stock: Any, scene_number: int) -> str:
        if isinstance(stock, str):
            return stock.strip().upper()
        if isinstance(stock, list):
            for item in stock:
                if not isinstance(item, dict):
                    continue
                if str(item.get("scene_number", item.get("scene"))) == str(scene_number):
                    return str(item.get("decision", item.get("stock_decision", ""))).strip().upper()
            return ""
        if not isinstance(stock, dict):
            return ""

        direct_value = stock.get(str(scene_number), stock.get(scene_number))
        if isinstance(direct_value, dict):
            return str(direct_value.get("decision", direct_value.get("stock_decision", ""))).strip().upper()
        if direct_value is not None:
            return str(direct_value).strip().upper()

        for key in ("by_scene", "scenes", "decisions"):
            nested = stock.get(key)
            if isinstance(nested, dict):
                value = nested.get(str(scene_number), nested.get(scene_number))
                if isinstance(value, dict):
                    return str(value.get("decision", value.get("stock_decision", ""))).strip().upper()
                if value is not None:
                    return str(value).strip().upper()
        return str(stock.get("decision", "")).strip().upper()

    @staticmethod
    def _ranking_quality_confirmed(ranking: dict[str, Any]) -> bool:
        for key in ("quality", "quality_acceptable", "approved", "selected_asset_quality"):
            value = ranking.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value >= (70 if value > 1 else 0.7)
            if isinstance(value, str):
                if value.strip().lower() in {"acceptable", "approved", "good", "high", "pass", "quality"}:
                    return True
        return False

    def _quality_agent_confirmed(self, quality: dict[str, Any] | list[dict[str, Any]], scene_number: int) -> bool:
        scene_quality = self._scene_data(quality, scene_number)
        for key in ("approved", "confirmed", "quality_confirmed", "pass", "accepted"):
            value = scene_quality.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"approved", "confirmed", "pass", "accepted", "true"}

        if isinstance(quality, dict):
            for key in ("approved", "confirmed", "quality_confirmed"):
                value = quality.get(key)
                if isinstance(value, bool):
                    return value
        return False

    def _resolve_prompts(
        self,
        project: Project,
        scene: TimelineScene,
        scene_number: int,
    ) -> tuple[str, str]:
        scene_prompts = self._scene_data(project.prompts, scene_number)
        director_scene = self._director_scene(project.director, scene_number)

        image_prompt = (
            str(scene_prompts.get("image_prompt", "")).strip()
            or scene.image_prompt
            or (director_scene.image_prompt if director_scene is not None else "")
            or self._fallback_image_prompt(scene, director_scene)
        )
        video_prompt = (
            str(scene_prompts.get("video_prompt", "")).strip()
            or scene.video_prompt
            or (director_scene.video_prompt if director_scene is not None else "")
            or self._fallback_video_prompt(scene, director_scene)
        )
        return image_prompt, video_prompt

    def _fallback_image_prompt(self, scene: TimelineScene, director_scene: Any) -> str:
        parts = [scene.visual, scene.goal, scene.emotion]
        if director_scene is not None:
            parts.append(director_scene.visual)
        return ". ".join(part for part in parts if part).strip()

    def _fallback_video_prompt(self, scene: TimelineScene, director_scene: Any) -> str:
        parts = [scene.visual, scene.transition, str(scene.camera.get("movement", ""))]
        if director_scene is not None:
            parts.append(director_scene.transition)
        return ". ".join(part for part in parts if part).strip()

    def _select_provider(
        self,
        project: Project,
        scene: TimelineScene,
        image_prompt: str,
        video_prompt: str,
    ) -> str:
        text = " ".join(
            [
                self._scene_text(scene),
                image_prompt.lower(),
                video_prompt.lower(),
                str(scene.camera.get("movement", "")).lower(),
                project.director.style.lower() if project.director is not None else "",
            ]
        )

        if self._has_higgsfield_signals(text):
            return "higgsfield"
        if self._has_kling_signals(text):
            return "kling"
        if self._has_runway_signals(text):
            return "runway"
        if self._has_seedance_signals(text):
            return "seedance"
        return "seedance"

    def _select_priority(self, scene: TimelineScene, index: int, total_scenes: int) -> str:
        text = self._scene_text(scene)
        shot = str(scene.camera.get("shot", "")).lower()

        if index == 0 or index == total_scenes - 1:
            return "high"
        if any(keyword in text for keyword in ("climax", "culmination", "emotional", "cry", "grief", "love")):
            return "high"
        if any(keyword in text for keyword in ("dialogue", "conversation", "important action", "key action")):
            return "medium"
        if any(keyword in shot for keyword in ("close-up", "closeup", "extreme close-up")):
            return "medium"
        if any(keyword in text for keyword in ("transition", "cutaway", "b-roll", "establishing")):
            return "low"
        if "establishing" in shot:
            return "low"
        return "medium"

    def _dependencies_for_scene(self, scenes: list[TimelineScene], index: int) -> list[int]:
        if index == 0:
            return []

        scene = scenes[index]
        previous_scene = scenes[index - 1]
        if self._depends_on_previous(scene, previous_scene):
            return [self._scene_number(previous_scene, fallback=index)]
        return []

    def _depends_on_previous(self, scene: TimelineScene, previous_scene: TimelineScene) -> bool:
        if scene.characters and previous_scene.characters:
            current = {character.strip().lower() for character in scene.characters if character.strip()}
            previous = {
                character.strip().lower() for character in previous_scene.characters if character.strip()
            }
            if current & previous:
                return True

        combined_text = self._scene_text(scene)
        if any(
            keyword in combined_text
            for keyword in (
                "continues",
                "continuation",
                "same character",
                "same action",
                "immediately after",
                "following scene",
            )
        ):
            return True

        if previous_scene.visual and scene.visual:
            previous_tokens = set(self._keywords(previous_scene.visual))
            current_tokens = set(self._keywords(scene.visual))
            overlap = previous_tokens & current_tokens
            if len(overlap) >= 3 and any(token in overlap for token in {"man", "woman", "child", "character"}):
                return True

        return False

    def _estimate_seconds(self, scene: TimelineScene, provider: str) -> int:
        duration = max(scene.duration, 3)
        profile = self._provider_profiles[provider]
        return profile["base_seconds"] + duration * profile["seconds_per_scene_second"]

    def _estimate_cost(self, scene: TimelineScene, provider: str) -> float:
        duration = max(scene.duration, 3)
        cost = duration * self._provider_profiles[provider]["cost_per_scene_second"]
        return round(cost, 4)

    def _build_notes(
        self,
        scene: TimelineScene,
        provider: str,
        priority: str,
        dependencies: list[int],
    ) -> str:
        parts = [f"provider={provider}", f"priority={priority}"]
        if dependencies:
            parts.append(f"depends_on_scene={dependencies[0]}")
        if scene.scene_type:
            parts.append(f"scene_type={scene.scene_type}")
        if scene.notes:
            parts.append(scene.notes)
        return "; ".join(parts)

    @staticmethod
    def _director_scene(director: DirectorPlan | None, scene_number: int) -> Any:
        if director is None:
            return None
        for scene in director.scenes:
            if scene.scene == scene_number:
                return scene
        return None

    @staticmethod
    def _scene_text(scene: TimelineScene) -> str:
        return " ".join(
            [
                scene.goal.lower(),
                scene.visual.lower(),
                scene.emotion.lower(),
                scene.dialogue.lower(),
                scene.scene_type.lower(),
                scene.notes.lower(),
                scene.transition.lower(),
                " ".join(character.lower() for character in scene.characters),
            ]
        )

    @staticmethod
    def _keywords(text: str) -> list[str]:
        return [token for token in text.lower().replace(",", " ").replace(".", " ").split() if len(token) > 2]

    @staticmethod
    def _has_seedance_signals(text: str) -> bool:
        return any(keyword in text for keyword in ("pixar", "animation", "animated", "stylized", "fantasy"))

    @staticmethod
    def _has_kling_signals(text: str) -> bool:
        return any(
            keyword in text
            for keyword in (
                "fast motion",
                "rapid",
                "transformation",
                "active action",
                "fight",
                "chase",
                "running",
            )
        )

    @staticmethod
    def _has_runway_signals(text: str) -> bool:
        return any(
            keyword in text
            for keyword in (
                "cinematic realism",
                "live action",
                "human",
                "documentary",
                "documentary style",
                "photorealistic",
                "realistic person",
            )
        )

    @staticmethod
    def _has_higgsfield_signals(text: str) -> bool:
        return any(
            keyword in text
            for keyword in (
                "drone",
                "fpv",
                "orbit",
                "complex camera movement",
                "crane",
                "dolly",
                "tracking shot",
            )
        )
