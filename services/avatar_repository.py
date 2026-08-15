"""Small JSON-backed persistence service for canonical AI Avatars."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from models.universe import Avatar


class AvatarRepository:
    """Persist canonical Avatar/Character records without introducing a second domain model."""

    def __init__(self, path: str | Path = "data/avatars.json") -> None:
        self.path = Path(path)

    def create(self, avatar: Avatar) -> Avatar:
        records = self._load()
        if any(item.id == avatar.id for item in records):
            raise ValueError(f"Avatar '{avatar.id}' already exists.")
        records.append(avatar)
        self._save(records)
        return avatar

    def get(self, avatar_id: str) -> Avatar | None:
        for avatar in self._load():
            if avatar.id == avatar_id:
                return avatar
        return None

    def update(self, avatar: Avatar) -> Avatar:
        records = self._load()
        for index, existing in enumerate(records):
            if existing.id == avatar.id:
                records[index] = avatar
                self._save(records)
                return avatar
        raise KeyError(f"Avatar '{avatar.id}' does not exist.")

    def delete(self, avatar_id: str) -> bool:
        records = self._load()
        filtered = [item for item in records if item.id != avatar_id]
        if len(filtered) == len(records):
            return False
        self._save(filtered)
        return True

    def list(self) -> list[Avatar]:
        return self._load()

    def _load(self) -> list[Avatar]:
        if not self.path.exists():
            return []
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise ValueError(f"Avatar store must contain a JSON list: {self.path}")
        return [Avatar.model_validate(item) for item in payload]

    def _save(self, avatars: list[Avatar]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            [avatar.model_dump(mode="json") for avatar in avatars],
            ensure_ascii=False,
            indent=2,
        )
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.path.parent, delete=False
        ) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(self.path)
