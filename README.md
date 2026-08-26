# AI Content Studio Personal

A modular, production-ready Python framework for orchestrating AI content-generation agents.

---

## Requirements

- Python 3.12+
- pip
- Docker (optional for deployment)
- `ffmpeg` for local browser assembly when running outside the provided container

---

## Quick start

```bash
# 1. Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill provider keys in .env only for local development.
# Never commit .env or provider secrets.

# 4. Run the CLI
python main.py

# Or run the browser MVP locally
python run_web.py
# Then open http://127.0.0.1:8787
```

The browser MVP intentionally uses the standard-library HTTP server; no frontend framework is required. The current free browser path supports Stock + Avatar assembly into a deterministic 9:16 MP4 and records completed projects in SQLite History.

### Deployment

`run_web.py` is the deployment entry point. It honors `HOST` and `PORT` (default `0.0.0.0:8787`). A lightweight readiness endpoint is exposed at `/health`; it reports service/storage readiness without returning provider secret values.

For a hosted deployment, configure provider credentials as the platform's environment secrets. Do **not** put real keys in `.env.example`, source files, Git history, or issue comments.

### Container deployment

The web MVP can also run as a small container. The image includes `ffmpeg`, which is required when multiple clips must be assembled into one MP4.

```bash
docker build -t ai-content-studio .
docker run --rm -p 8787:8787 --env-file .env ai-content-studio
```

The container listens on `0.0.0.0` and honors `PORT` (default `8787`). For hosted deployment, keep provider secrets in the host's secret/environment configuration rather than committing `.env`.

---

## Browser MVP flow

The current browser flow has two complementary paths:

1. **Generation path:** topic → existing storyboard/generation pipeline → provider generation → 9:16 MP4 export.
2. **Free Stock + Avatar path:** choose HTTPS Stock clips and an HTTPS Avatar reference → validate requests → assemble with `ffmpeg` → persist the completed project in History.

The Stock + Avatar path applies download-size limits and rejects private, loopback, link-local, and reserved network targets, including redirect targets. This is intentionally conservative because user-supplied URLs are fetched server-side.

For the first real provider smoke-test, use the deployed browser MVP and provide `FAL_KEY` only through the runtime environment. The provider secret must never be committed.

---

## Project structure

```
AI-Content-Studio-Personal/
├── main.py                  # CLI entry point
├── web_ui.py                # Browser UI/server building blocks
├── run_web.py               # Deployment entry point (HOST/PORT aware)
├── Dockerfile               # Minimal web deployment image
├── .dockerignore
├── .env.example             # Environment variable template (no real secrets)
├── requirements.txt
│
├── config/                  # Settings
├── core/                    # App, routing, orchestration, logging
├── agents/                  # AI/content agents
├── services/                # Application orchestration and provider adapters
├── models/                  # Domain/application models, including AI Universe
├── prompts/                 # Prompt templates
├── assets/                  # Static input assets
└── output/                  # Generated content (git-ignored)
```

---

## MVP architecture

The first browser workflow preserves the existing domain/application boundaries:

`Project → StoryboardContext → GenerationPlan → GenerationPipelineService → GeneratedAsset persistence → 9:16 MP4 export`

AI Universe remains a first-class domain capability. Universe-aware projects continue to resolve canonical Characters and Locations through application services; the thin UI never creates competing avatar/character models or bypasses those boundaries.

---

## Pipeline

The current execution order is:

1. `IdeaAgent.run(project: Project) -> Project`
2. `DirectorAgent.run(project: Project) -> Project`
3. `StoryboardContextService` converts the project into executable storyboard context.
4. `GenerationPlanner` creates deterministic provider-neutral generation jobs.
5. `GenerationPipelineService` executes the selected provider, persists generated clips, and exports a deterministic 9:16 MP4.

The `PipelineOrchestrator` controls the earlier agent workflow. Application services own generation/export orchestration.

---

## Adding a new agent

1. Create `agents/my_agent.py` and subclass `BaseAgent`.
2. Register a handler in `core/app.py`.
3. Add focused tests.

Keep business logic in agents/services rather than UI handlers.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `AI Content Studio Personal` | Display name |
| `APP_ENV` | `development` | Environment tag |
| `DEBUG` | `false` | Verbose logging |
| `FAL_KEY` | _(empty)_ | fal provider credential; runtime secret only |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI key |
| `ANTHROPIC_API_KEY` | _(empty)_ | Anthropic key |
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini key |
| `PEXELS_API_KEY` | _(empty)_ | Pexels Stock API key |
| `OPENROUTER_API_KEY` | _(empty)_ | OpenRouter key |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | OpenRouter model |
| `OUTPUT_DIR` | `output` | Generated-content directory |
| `ASSETS_DIR` | `assets` | Static-assets directory |
| `LOG_FILE` | _(empty)_ | Optional log file path |
| `HOST` | `0.0.0.0` | Web server bind address |
| `PORT` | `8787` | Web server port |

For production, set secrets in the deployment platform rather than storing them in files. `/health` intentionally does not expose secret values.

---

## Issue #30 smoke-test checklist

The first real provider/deployment validation is intentionally a runtime test, not a mocked CI test:

1. Deploy `run_web.py` or the Docker image.
2. Confirm `/health` reports readiness.
3. Ensure `FAL_KEY` is supplied by the runtime secret store.
4. Start one real 9:16 generation from the browser UI.
5. Verify status transitions are honest: queued → generating → done/failed.
6. Confirm the resulting MP4 is persisted in SQLite History.
7. Restart the runtime and confirm the project remains visible in Recent Projects.
8. Record any provider/runtime failure as a focused follow-up issue; never commit the secret.

---

## License

MIT
