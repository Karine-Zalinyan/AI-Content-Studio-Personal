from services.avatar_browser_service import AvatarBrowserService


def test_avatar_browser_service_creates_and_lists_canonical_avatar(tmp_path) -> None:
    service = AvatarBrowserService(tmp_path / "avatars.json")
    created = service.create(
        name="Lumi",
        appearance="Cream-white fur, amber eyes",
        visual_reference="https://example.com/lumi.png",
    )

    assert created["name"] == "Lumi"
    assert created["visual_reference"] == "https://example.com/lumi.png"
    assert service.list()[0]["id"] == created["id"]


def test_avatar_browser_service_rejects_insecure_reference(tmp_path) -> None:
    service = AvatarBrowserService(tmp_path / "avatars.json")

    try:
        service.create(name="Bad", visual_reference="http://example.com/avatar.png")
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("Expected HTTP Avatar reference to be rejected")
