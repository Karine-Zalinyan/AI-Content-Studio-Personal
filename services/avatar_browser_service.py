"""Browser-facing service for the canonical Avatar/Character library."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from models.universe import Avatar, CharacterBible
from services.avatar_repository import AvatarRepository


class AvatarBrowserService:
    """Create and list canonical Avatars without introducing a second domain model."""

    def __init__(self, path: str | Path) -> None:
        self.repository = AvatarRepository(path)

    def list(self) -> list[dict[str, object]]:
        return [self._serialize(avatar) for avatar in self.repository.list()]

    def create(
        self,
        *,
        name: str,
        appearance: str = "",
        visual_reference: str = "",
    ) -> dict[str, object]:
        name = name.strip()
        if not name:
            raise ValueError("Avatar name cannot be empty")
        if len(name) > 120:
            raise ValueError("Avatar name is too long")
        visual_reference = visual_reference.strip()
        if visual_reference:
            parsed = urlparse(visual_reference)
            if parsed.scheme != "https" or not parsed.hostname:
                raise ValueError("Avatar reference must use a valid HTTPS URL")
        avatar = Avatar(
            name=name,
            bible=CharacterBible(
                appearance=appearance.strip(),
                visual_reference=visual_reference,
            ),
        )
        return self._serialize(self.repository.create(avatar))

    @staticmethod
    def _serialize(avatar: Avatar) -> dict[str, object]:
        return {
            "id": avatar.id,
            "name": avatar.name,
            "appearance": avatar.bible.appearance,
            "visual_reference": avatar.bible.visual_reference,
        }
