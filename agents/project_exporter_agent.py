"""
ProjectExporterAgent

Exports the project into a structured folder without mutating project state.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.base import BaseAgent
from models.project import DirectorPlan, GeneratedAsset, Project, TimelineScene
from utils.file_utils import write_json, write_text


class ProjectExporterAgent(BaseAgent):
    """Export the full project and related files into a structured directory."""

    def run(self, project: Project) -> Project:
        export_dir = self._build_export_dir(project)
        assets_stock_dir = export_dir / "assets" / "stock"
        assets_ai_dir = export_dir / "assets" / "ai"
        video_dir = export_dir / "video"

        assets_stock_dir.mkdir(parents=True, exist_ok=True)
        assets_ai_dir.mkdir(parents=True, exist_ok=True)
        video_dir.mkdir(parents=True, exist_ok=True)

        self._export_json_files(project, export_dir)
        self._copy_stock_assets(project, assets_stock_dir)
        self._copy_ai_assets(project, assets_ai_dir)
        self._copy_final_video(project, video_dir)
        write_text(export_dir / "report.md", self._build_report(project))

        self.logger.info("Project exported to %s", export_dir)
        return project

    def _build_export_dir(self, project: Project) -> Path:
        root = Path(__file__).resolve().parent.parent
        topic_slug = self._slugify(project.topic)
        return root / "exports" / topic_slug

    def _export_json_files(self, project: Project, export_dir: Path) -> None:
        write_json(export_dir / "project.json", project.model_dump(mode="json"))
        write_json(export_dir / "project_export.json", project.model_dump(mode="json"))
        write_json(export_dir / "idea.json", self._dump_model(project.idea))
        write_json(export_dir / "director.json", self._dump_model(project.director))
        write_json(export_dir / "stock.json", project.stock)
        write_json(export_dir / "prompts.json", project.prompts)
        write_json(export_dir / "timeline.json", [scene.model_dump(mode="json") for scene in project.timeline])
        write_json(export_dir / "quality.json", project.quality)
        write_json(
            export_dir / "generation_jobs.json",
            [job.model_dump(mode="json") for job in project.generation_jobs],
        )
        write_json(export_dir / "asset_ranking.json", project.asset_ranking)
        write_json(
            export_dir / "generation_logs.json",
            [log.model_dump(mode="json") for log in project.generation_logs],
        )

    def _copy_stock_assets(self, project: Project, destination: Path) -> None:
        for index, video_path in enumerate(project.assets.videos, start=1):
            self._copy_file_if_exists(video_path, destination / f"scene_{index}{Path(video_path).suffix or '.mp4'}")

    def _copy_ai_assets(self, project: Project, destination: Path) -> None:
        for asset in project.assets.ai_videos:
            self._copy_generated_asset(asset, destination)

    def _copy_generated_asset(self, asset: GeneratedAsset, destination: Path) -> None:
        source = asset.file_path
        suffix = Path(source).suffix or ".mp4"
        filename = f"scene_{asset.scene_number}_{asset.provider}{suffix}"
        self._copy_file_if_exists(source, destination / filename)

        if asset.preview_path:
            preview_suffix = Path(asset.preview_path).suffix or ".jpg"
            preview_name = f"scene_{asset.scene_number}_{asset.provider}_preview{preview_suffix}"
            self._copy_file_if_exists(asset.preview_path, destination / preview_name)

    def _copy_final_video(self, project: Project, destination: Path) -> None:
        if project.video.file_path:
            suffix = Path(project.video.file_path).suffix or ".mp4"
            self._copy_file_if_exists(project.video.file_path, destination / f"final_video{suffix}")

    def _copy_file_if_exists(self, source: str | Path, destination: Path) -> None:
        source_path = Path(source)
        if not source_path.exists() or not source_path.is_file():
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)

    def _build_report(self, project: Project) -> str:
        scenes = self._resolve_scenes(project)
        ai_jobs_by_scene = {job.scene_number: job for job in project.generation_jobs}
        ai_assets_by_scene = {asset.scene_number: asset for asset in project.assets.ai_videos}
        total_cost = sum(log.cost for log in project.generation_logs)
        total_generation_time = sum(log.generation_time for log in project.generation_logs)
        ai_scene_count = len(ai_jobs_by_scene)
        stock_scene_count = max(len(scenes) - ai_scene_count, 0)
        generated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        project_title = self._project_title(project)
        total_duration = self._total_duration(project, scenes)
        quality = self._quality_summary(project.quality)

        lines = [
            f"# {project_title}",
            "",
            "## Информация",
            "",
            f"- **Название проекта:** {project_title}",
            f"- **Тема:** {project.topic}",
            f"- **Дата:** {generated_at}",
            f"- **Общая длительность:** {total_duration} сек",
            "",
            "## Сцены",
            "",
        ]

        for index, scene in enumerate(scenes, start=1):
            scene_number = self._scene_number(scene, index)
            job = ai_jobs_by_scene.get(scene_number)
            ai_asset = ai_assets_by_scene.get(scene_number)
            asset_mode = "AI" if job is not None else "STOCK"
            asset_name = self._scene_asset_name(project, scene_number, ai_asset)
            provider = job.provider if job is not None else "-"
            description = self._scene_description(scene)
            duration = self._scene_duration(scene)

            lines.extend(
                [
                    f"### Scene {scene_number}",
                    "",
                    f"- **Описание:** {description}",
                    f"- **Тип:** {asset_mode}",
                    f"- **Использованный ассет:** {asset_name}",
                    f"- **Провайдер:** {provider}",
                    f"- **Длительность:** {duration} сек",
                    "",
                ]
            )

        lines.extend(
            [
                "## Генерация",
                "",
                f"- **Количество AI сцен:** {ai_scene_count}",
                f"- **Количество STOCK сцен:** {stock_scene_count}",
                f"- **Стоимость:** ${total_cost:.4f}",
                f"- **Время генерации:** {total_generation_time:.3f} сек",
                "",
                "## Качество",
                "",
                f"- **Score:** {quality['score']}",
                f"- **Warnings:** {quality['warnings']}",
                f"- **Errors:** {quality['errors']}",
                f"- **Recommendations:** {quality['recommendations']}",
                "",
            ]
        )

        return "\n".join(lines)

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
    def _dump_model(model: Any) -> Any:
        if model is None:
            return {}
        if hasattr(model, "model_dump"):
            return model.model_dump(mode="json")
        return model

    @staticmethod
    def _project_title(project: Project) -> str:
        if project.export.title:
            return project.export.title
        if project.idea is not None and project.idea.title:
            return project.idea.title
        return project.topic

    @staticmethod
    def _scene_number(scene: TimelineScene, fallback: int) -> int:
        return int(scene.scene_number or fallback)

    @staticmethod
    def _scene_duration(scene: TimelineScene) -> int:
        return int(scene.duration or 0)

    def _scene_description(self, scene: TimelineScene) -> str:
        parts = [scene.goal, scene.visual, scene.emotion]
        text = ". ".join(part for part in parts if part).strip()
        return text or "-"

    def _scene_asset_name(
        self,
        project: Project,
        scene_number: int,
        ai_asset: GeneratedAsset | None,
    ) -> str:
        if ai_asset is not None:
            return Path(ai_asset.file_path).name or ai_asset.provider
        index = scene_number - 1
        if 0 <= index < len(project.assets.videos):
            return Path(project.assets.videos[index]).name
        return "-"

    def _total_duration(self, project: Project, scenes: list[TimelineScene]) -> int:
        if project.video.duration:
            return int(project.video.duration)
        if project.director is not None:
            return int(project.director.duration)
        return sum(self._scene_duration(scene) for scene in scenes)

    def _quality_summary(self, quality: Any) -> dict[str, str]:
        if not isinstance(quality, dict):
            return {
                "score": "-",
                "warnings": "-",
                "errors": "-",
                "recommendations": "-",
            }

        return {
            "score": str(quality.get("score", quality.get("overall_score", "-"))),
            "warnings": self._format_quality_field(quality.get("warnings", [])),
            "errors": self._format_quality_field(quality.get("errors", [])),
            "recommendations": self._format_quality_field(quality.get("recommendations", [])),
        }

    @staticmethod
    def _format_quality_field(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value) or "-"
        if isinstance(value, dict):
            return ", ".join(f"{key}: {item}" for key, item in value.items()) or "-"
        if value in (None, "", [], {}):
            return "-"
        return str(value)

    @staticmethod
    def _slugify(value: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
        sanitized = re.sub(r"_+", "_", sanitized).strip("_")
        return sanitized or "project"
