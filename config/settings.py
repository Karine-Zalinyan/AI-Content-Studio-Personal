"""
Central application settings loaded from environment / .env file.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = Field(default="AI Content Studio Personal")
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)

    # ── AI providers ─────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")
    openrouter_model: str = Field(default="openai/gpt-4o-mini")
    pexels_api_key: str = Field(default="")

    # ── Paths ─────────────────────────────────────────────────────────────────
    output_dir: Path = Field(default=Path("output"))
    assets_dir: Path = Field(default=Path("assets"))
    log_file: str = Field(default="")  # e.g. "output/app.log" – empty = no file

    def ensure_dirs(self) -> None:
        """Create output / assets directories if they do not exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)


# Module-level singleton – import this everywhere
settings = Settings()
