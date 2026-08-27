import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import services.stock_avatar_ui_server as ui_server
from services.avatar_browser_service import AvatarBrowserService
from services.deployment_health_service import DeploymentHealthService


def test_browser_mvp_health_and_avatar_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(ui_server, "AVATARS", AvatarBrowserService(tmp_path / "avatars.json"))
    monkeypatch.setattr(ui_server, "HEALTH", DeploymentHealthService(tmp_path))

    server = ThreadingHTTPServer(("127.0.0.1", 0), ui_server.StockAvatarStudioHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"

        with urllib.request.urlopen(f"{base}/health", timeout=5) as response:
            health = json.load(response)
        assert health == {"status": "ok", "storage": "ok"}

        request = urllib.request.Request(
            f"{base}/api/avatars",
            data=json.dumps(
                {
                    "name": "Lumi",
                    "appearance": "Cream-white fur, amber eyes",
                    "visual_reference": "https://cdn.example/lumi.png",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            created = json.load(response)
        assert created["avatar"]["name"] == "Lumi"

        with urllib.request.urlopen(f"{base}/api/avatars", timeout=5) as response:
            avatars = json.load(response)
        assert avatars["avatars"][0]["name"] == "Lumi"
        assert avatars["avatars"][0]["visual_reference"] == "https://cdn.example/lumi.png"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
