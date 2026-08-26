"""Browser-facing service for the canonical Avatar/Character library."""

from __future__ import annotations

from pathlib import Path

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
        if visual_reference and not visual_reference.startswith("https://"):
            raise ValueError("Avatar reference must use HTTPS")
        avatar = Avatar(
            name=name,
            bible=CharacterBible(
                appearance=appearance.strip(),
                visual_reference=visual_reference.strip(),
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
