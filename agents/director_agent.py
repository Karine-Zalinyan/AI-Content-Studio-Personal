"""
DirectorAgent

Expands a viral idea (Idea JSON) into a detailed cinematic scene breakdown
optimized for AI image generation, AI video generation, and automatic editing.
"""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

import certifi
import httpx

from agents.base import BaseAgent
from models.project import DirectorPlan, Project


class DirectorAgent(BaseAgent):
    """Expand an idea into a production-ready scene breakdown."""

    _api_url = "https://openrouter.ai/api/v1/chat/completions"

    def direct(self, project: Project) -> Project:
        """Expand the project's idea JSON into a cinematic scene breakdown."""
        payload = self._build_payload(project.idea.model_dump())
        response = self._post(payload)
        content = self._extract_content(response)
        project.director = DirectorPlan.model_validate(self._parse_json(content))
        return project

    def run(self, project: Project) -> Project:
        return self.direct(project)

    def _build_payload(self, idea: dict[str, Any]) -> dict[str, Any]:
        idea_str = json.dumps(idea, ensure_ascii=False, indent=2)
        system_prompt = (
            "You are an expert film director for YouTube Shorts optimizing for AI-generated visuals and video. "
            "Your task is to take a video idea and break it down into a detailed cinematic scene-by-scene breakdown. "
            "You MUST NOT invent a different story or change the narrative. "
            "You ONLY expand the idea into 8–12 scenes, each carefully crafted for AI image generation, "
            "AI video generation, and automatic editing. "
            "Every field must be specific, visual, and actionable for AI systems. "
            "Total duration must be exactly 60 seconds. "
            "Each scene must have a clear cinematic purpose that advances the narrative. "
            "Return valid JSON with exactly this structure: "
            '{"duration": 60, "style": "...", "aspect_ratio": "9:16", "fps": 30, '
            '"scenes": [{"scene": 1, "duration": N, "goal": "...", "visual": "...", '
            '"camera": {"shot": "...", "movement": "...", "angle": "..."}, '
            '"lighting": {"type": "...", "temperature": "..."}, '
            '"emotion": "...", "voiceover": "...", '
            '"music": {"genre": "...", "intensity": "..."}, '
            '"sfx": ["...", "..."], '
            '"transition": "...", '
            '"image_prompt": "...", '
            '"video_prompt": "..."}]} '
            "Camera shot types: wide, medium, close-up, extreme close-up, establishing. "
            "Camera movements: static, pan, tilt, dolly-in, dolly-out, tracking, crane, orbit. "
            "Camera angles: eye-level, high, low, dutch. "
            "Lighting types: key, fill, back, rim, practical, ambient, natural. "
            "Light temperature: cool, warm, neutral. "
            "Music intensity: minimal, subtle, moderate, intense, climactic. "
            "SFX as array of specific sounds. "
            "image_prompt: detailed visual description optimized for text-to-image AI (e.g., Midjourney, DALL-E). "
            "video_prompt: concise cinematic description optimized for text-to-video AI (e.g., Runway, Pika). "
            "Optimize every field for AI generation and automatic editing workflows."
        )
        user_prompt = (
            f"Expand this idea into a detailed scene breakdown:\n\n{idea_str}\n\n"
            "Rules:\n"
            "1. NEVER change the story. ONLY expand the core_story into scenes.\n"
            "2. Create 8–12 scenes.\n"
            "3. Total duration = 60 seconds.\n"
            "4. For each scene:\n"
            "   - camera: structured {shot, movement, angle}\n"
            "   - lighting: structured {type, temperature}\n"
            "   - music: structured {genre, intensity}\n"
            "   - sfx: array of sound descriptions\n"
            "   - image_prompt: detailed visual for AI image generation\n"
            "   - video_prompt: cinematic description for AI video generation\n"
            "5. Optimize image_prompt for Midjourney/DALL-E quality output.\n"
            "6. Optimize video_prompt for Runway/Pika quality output.\n"
            "7. All other fields (visual, goal, emotion, voiceover, transition) remain descriptive.\n"
            "8. Return ONLY the JSON. No commentary."
        )
        return {
            "model": self.settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required in the .env file.")

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": self.settings.app_name,
        }

        try:
            with httpx.Client(timeout=60, verify=certifi.where()) as client:
                response = client.post(self._api_url, json=payload, headers=headers)
                response.raise_for_status()
                raw_response = response.text
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            message = detail or exc.response.reason_phrase
            raise RuntimeError(
                f"OpenRouter request failed ({exc.response.status_code}): {message}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc

        try:
            return json.loads(raw_response)
        except JSONDecodeError as exc:
            raise ValueError("OpenRouter returned invalid JSON response.") from exc

    @staticmethod
    def _extract_content(response: dict[str, Any]) -> str:
        choices = response.get("choices") or []
        if not choices:
            raise ValueError("OpenRouter response did not include any choices.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenRouter response did not include text content.")
        return content.strip()

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
        except JSONDecodeError as exc:
            raise ValueError(f"OpenRouter returned invalid JSON: {content}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("OpenRouter response JSON must be an object.")

        return parsed
