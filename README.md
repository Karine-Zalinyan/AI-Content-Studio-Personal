# AI Content Studio Personal

A modular, production-ready Python framework for orchestrating AI content-generation agents.

---

## Requirements

- Python 3.12+
- pip

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
# Open .env and fill in your API keys

# 4. Run the CLI
python main.py

# Or run the thin browser MVP
python web_ui.py
# Then open http://127.0.0.1:8787
```

The browser MVP intentionally exposes only the first production loop: topic → existing storyboard/generation pipeline → 9:16 MP4 preview/export. It uses the standard library HTTP server, so no frontend framework is required.

---

## Project structure

```
AI-Content-Studio-Personal/
├── main.py                  # CLI entry point
├── web_ui.py                # Thin browser MVP entry point
├── .env.example             # Environment variable template
├── requirements.txt
│
├── config/
│   └── settings.py          # Pydantic-settings singleton (loads .env)
│
├── core/
│   ├── app.py               # App class – menu loop & route wiring
│   ├── orchestrator.py      # PipelineOrchestrator – controls agent order
│   ├── router.py            # Command router (key → handler)
│   └── logger.py            # Logging bootstrap
│
├── agents/                  # AI/content agents
├── services/                # Application orchestration and provider adapters
├── models/                  # Domain/application models, including AI Universe
├── prompts/                 # Prompt templates (.txt / .md / .jinja2)
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

| Variable            | Default                    | Description                  |
|---------------------|----------------------------|------------------------------|
| `APP_NAME`          | AI Content Studio Personal | Display name                 |
| `APP_ENV`           | development                | Environment tag              |
| `DEBUG`             | false                      | Verbose logging              |
| `OPENAI_API_KEY`    | _(empty)_                  | OpenAI key                   |
| `ANTHROPIC_API_KEY` | _(empty)_                  | Anthropic key                |
| `GEMINI_API_KEY`    | _(empty)_                  | Google Gemini key            |
| `OPENROUTER_API_KEY`| _(empty)_                  | OpenRouter key               |
| `OPENROUTER_MODEL`  | `openai/gpt-4o-mini`       | OpenRouter model             |
| `OUTPUT_DIR`        | output                     | Generated-content directory  |
| `ASSETS_DIR`        | assets                     | Static-assets directory      |
| `LOG_FILE`          | _(empty)_                  | Optional log file path       |

---

## License

MIT
