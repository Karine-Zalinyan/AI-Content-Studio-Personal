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
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Open .env and fill in your API keys

# 4. Run the application
python main.py
```

---

## Project structure

```
AI-Content-Studio-Personal/
├── main.py                  # Entry point
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
├── agents/
│   └── base.py              # BaseAgent ABC – all agents extend this
│
├── services/
│   └── base.py              # BaseService ABC – all services extend this
│
├── models/
│   ├── base.py              # AppBaseModel (Pydantic) – shared by all models
│   └── project.py           # Shared Project / Idea / DirectorPlan models
│
├── utils/
│   └── file_utils.py        # read/write helpers for text & JSON
│
├── prompts/                  # Prompt templates (.txt / .md / .jinja2)
├── assets/                   # Static input assets
└── output/                   # Generated content (git-ignored)
```

---

## Pipeline

The current execution order is:

1. `IdeaAgent.run(project: Project) -> Project`
2. `DirectorAgent.run(project: Project) -> Project`

The `PipelineOrchestrator` controls execution order. Agents do not call each other.

---

## Adding a new agent

1. Create `agents/my_agent.py` and subclass `BaseAgent`:

```python
from agents.base import BaseAgent
from models.project import Project

class MyAgent(BaseAgent):
    def run(self, project: Project) -> Project:
        # ... update the shared project ...
        return project
```

2. Register a handler in `core/app.py`:

```python
# In App._register_routes():
self.router.register("2", self._handle_my_feature)

# Add a stub handler:
def _handle_my_feature(self) -> None:
    from agents.my_agent import MyAgent
    MyAgent().run(topic="...")
```

3. Add a menu entry to `MENU_ITEMS` in `core/app.py`:

```python
MENU_ITEMS = [
    ("1", "Create Viral Video"),
    ("2", "My New Feature"),   # ← new
]
```

---

## Environment variables

| Variable           | Default                    | Description                  |
|--------------------|----------------------------|------------------------------|
| `APP_NAME`         | AI Content Studio Personal | Display name                 |
| `APP_ENV`          | development                | Environment tag              |
| `DEBUG`            | false                      | Verbose logging              |
| `OPENAI_API_KEY`   | _(empty)_                  | OpenAI key                   |
| `ANTHROPIC_API_KEY`| _(empty)_                  | Anthropic key                |
| `GEMINI_API_KEY`   | _(empty)_                  | Google Gemini key            |
| `OPENROUTER_API_KEY`| _(empty)_                 | OpenRouter key               |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini`       | OpenRouter model             |
| `OUTPUT_DIR`       | output                     | Generated-content directory  |
| `ASSETS_DIR`      | assets                     | Static-assets directory      |
| `LOG_FILE`         | _(empty)_                  | Optional log file path       |

---

## License

MIT
