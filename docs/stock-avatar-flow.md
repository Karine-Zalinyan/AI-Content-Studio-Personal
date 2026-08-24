# Free Stock + Avatar browser flow

The browser-facing flow is intentionally provider-free:

1. User enters a short topic.
2. User searches Pexels for portrait stock clips.
3. User selects up to six HTTPS clips.
4. User optionally supplies a canonical Avatar reference.
5. `StockAvatarWebService` validates the request.
6. `StockAvatarAssemblyService` downloads, normalizes, overlays the Avatar, concatenates clips, and exports 1080x1920 MP4.
7. The resulting Project stores stock assembly metadata and the output path for History.

The paid generation provider remains a separate path and is not required for this flow.
