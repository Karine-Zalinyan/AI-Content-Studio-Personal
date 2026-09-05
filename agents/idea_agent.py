"""
IdeaAgent

Generates viral food YouTube Shorts concepts using OpenRouter.
"""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

import certifi
import httpx

from agents.base import BaseAgent
from models.project import Idea, Project
from config.food_niche import food_profile_text


class IdeaAgent(BaseAgent):
    """Generate a single viral short-form content idea."""

    _api_url = "https://openrouter.ai/api/v1/chat/completions"

    def generate(self, project: Project) -> Project:
        """Generate and store the idea on the given project."""
        payload = self._build_payload(project.topic)
        response = self._post(payload)
        content = self._extract_content(response)
        project.idea = Idea.model_validate(self._parse_json(content))
        return project

    def run(self, project: Project) -> Project:
        return self.generate(project)

    def _build_payload(self, topic: str) -> dict[str, Any]:
        system_prompt = (
            "You are an expert short-form food content strategist for international English-language YouTube Shorts. " + food_profile_text() + " "
            "The user's topic is mandatory and must always stay at the absolute center of every idea. "
            "Never drift away from the topic, never replace it with a different subject, and never generalize it. "
            "If the topic is 'Cat', every idea and every part of the core story must be about cats. "
            "If the topic is 'Lost Child', every idea and every part of the core story must be about a lost child. "
            "Generate exactly 10 distinct viral food ideas ONLY about the topic. Favor transformation, curiosity, sensory payoff, and repeatable series formats. "
            "Score all 10 ideas for retention, visual curiosity, appetite appeal, sensory payoff, rewatch value, and series potential. "
            "Select the single best idea. Return ONLY the best idea as valid JSON with exactly these keys: "
            '"title", "hook", "core_story", "emotion", "thumbnail", "viral_score". '
            "core_story must be maximum 5 sentences describing only the narrative concept. "
            "Do NOT include: scene breakdown, camera directions, lighting, music, editing, transitions, or production notes. "
            'The viral_score must be an integer from 0 to 100.'
        )
        user_prompt = (
            f"Topic: {topic}\n\n"
            "The topic is mandatory. Generate 10 viral ideas ONLY about this exact topic, score them, "
            "select the best one, and return only that final idea. "
            "The core_story must be a maximum 5 sentences narrative concept—nothing else. "
            "Do NOT write a screenplay, scene breakdown, or production notes."
        )
        return {
            "model": self.settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.9,
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
