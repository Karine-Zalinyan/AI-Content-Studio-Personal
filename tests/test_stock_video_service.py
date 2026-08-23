from __future__ import annotations

from services.stock_video_service import StockVideoSearchService


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, *, params, headers):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return FakeResponse(self.payload)


def test_search_normalizes_portrait_results_and_prefers_highest_res_preview() -> None:
    client = FakeClient(
        {
            "videos": [
                {
                    "id": 7,
                    "duration": 12,
                    "width": 720,
                    "height": 1280,
                    "user": {"name": "Pexels Creator"},
                    "url": "https://www.pexels.com/video/7/",
                    "image": "https://images.pexels.com/videos/7.jpeg",
                    "video_files": [
                        {"width": 360, "height": 640, "link": "https://player.pexels.com/videos/7-small.mp4"},
                        {"width": 720, "height": 1280, "link": "https://player.pexels.com/videos/7-large.mp4"},
                    ],
                }
            ]
        }
    )
    service = StockVideoSearchService(api_key="pexels-key", client=client)

    results = service.search("night city")

    assert client.calls == [
        {
            "url": service.search_url,
            "params": {"query": "night city", "per_page": 6, "orientation": "portrait"},
            "headers": {"Authorization": "pexels-key"},
        }
    ]
    assert results == [
        {
            "id": "7",
            "title": "Clip by Pexels Creator",
            "duration_seconds": 12,
            "width": 720,
            "height": 1280,
            "orientation": "portrait",
            "thumbnail_url": "https://images.pexels.com/videos/7.jpeg",
            "source_url": "https://www.pexels.com/video/7/",
            "preview_url": "https://player.pexels.com/videos/7-large.mp4",
        }
    ]


def test_search_filters_insecure_preview_links() -> None:
    client = FakeClient(
        {
            "videos": [
                {
                    "id": 8,
                    "url": "https://www.pexels.com/video/8/",
                    "video_files": [
                        {"width": 720, "height": 1280, "link": "http://player.pexels.com/videos/8-insecure.mp4"},
                        {"width": 360, "height": 640, "link": "https://player.pexels.com/videos/8-secure.mp4"},
                    ],
                }
            ]
        }
    )
    service = StockVideoSearchService(api_key="pexels-key", client=client)

    results = service.search("forest trail")

    assert results[0]["preview_url"] == "https://player.pexels.com/videos/8-secure.mp4"
