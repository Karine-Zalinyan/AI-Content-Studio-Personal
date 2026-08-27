from services.avatar_browser_service import AvatarBrowserService


def test_avatar_browser_service_accepts_valid_https_reference(tmp_path) -> None:
    service = AvatarBrowserService(tmp_path / "avatars.json")

    avatar = service.create(
        name="Lumi",
        appearance="Cream-white fur, amber eyes",
        visual_reference="https://example.com/avatar.png",
    )

    assert avatar["name"] == "Lumi"
    assert avatar["visual_reference"] == "https://example.com/avatar.png"


def test_avatar_browser_service_rejects_http_reference(tmp_path) -> None:
    service = AvatarBrowserService(tmp_path / "avatars.json")

    try:
        service.create(name="Bad", visual_reference="http://example.com/avatar.png")
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("Expected HTTP Avatar reference to be rejected")


def test_avatar_browser_service_rejects_non_url_https_prefix(tmp_path) -> None:
    service = AvatarBrowserService(tmp_path / "avatars.json")

    try:
        service.create(name="Bad", visual_reference="https://")
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("Expected invalid Avatar reference to be rejected")
