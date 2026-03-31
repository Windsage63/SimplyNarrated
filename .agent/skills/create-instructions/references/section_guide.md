# Section Guide

Templates and examples for every section of an `AGENTS.md` file, plus guidance for `.instructions.md` files. Not every project needs every section — include only what's relevant.

---

## Part 1: AGENTS.md Sections

### Project Overview

2-3 sentences. What the app does, primary language/framework, and any unusual characteristics.

**Good:**

```markdown
## Project Overview

SimplyNarrated is a local web application that converts books and documents into MP3 audiobooks using the Kokoro-82M TTS model running locally on GPU. FastAPI backend with a vanilla JS SPA frontend, no external databases or cloud dependencies.
```

**Bad — restates what an agent can infer:**

```markdown
## Project Overview

SimplyNarrated is a web application. It uses Python for the backend and JavaScript for the frontend. Python is a programming language...
```

### Commands

Exact, verified, copy-pasteable commands. Group by purpose. Include the full runtime path if non-standard.

```markdown
## Commands

### Run the app
python_embedded\python.exe -m uvicorn src.main:app --port 8010

### Run tests
python_embedded\python.exe -m pytest tests/ -m "not slow"

### Install dependencies
pip install -r requirements.txt
```

**Key considerations:**

  - If using an embedded/vendored runtime, always show its path
  - Include common flags (e.g., `-m "not slow"` for skipping GPU tests)
  - If Docker is involved, show Docker commands
  - Note when a command is a stub or doesn't exist yet

### Environment

Only when the runtime is non-standard. Skip for standard venv/node_modules projects.

```markdown
## Environment

- Python 3.12 via `python_embedded/` directory (vendored, not a global install)
- Do not use a virtual environment — the embedded Python has all dependencies
- spaCy model vendored under `models/en_core_web_sm/`
```

### Architecture

ASCII tree of source structure with one-line descriptions. Orient the agent, not deeper.

```markdown
## Architecture

src/
├── main.py              # App init, lifespan, static file mounting
├── api/
│   └── routes.py        # All HTTP endpoints (single router)
├── core/
│   ├── pipeline.py      # Orchestrator: parse → chunk → TTS → encode
│   ├── tts_engine.py    # TTS model wrapper
│   └── library.py       # File-based book metadata and bookmarks
└── models/
    └── schemas.py       # Pydantic request/response models
```

**Guidelines:**

  - Only source directories, not `node_modules/` or `__pycache__/`
  - One-line comment per file is sufficient
  - For monorepos, show top-level structure and link to subfolder docs

### Data Layer

Only when the storage approach isn't obvious.

```markdown
## Data Layer

No database. All persistence is file-based under `data/`:
- `data/library/{book_id}/metadata.json` — Book metadata
- `data/library/{book_id}/chapter_NN.mp3` — Audio files
- `data/jobs.json` — Job queue (survives restarts)
```

### Key Conventions

**The highest-value section.** Include only patterns the agent would get wrong without being told. Each convention: pattern name, 1-sentence explanation, code example.

```markdown
## Key Conventions

### Singletons via module-level getters
Core services are initialized at startup and accessed via getter functions:
from src.core.job_manager import get_job_manager
jm = get_job_manager()

### Async throughout
All route handlers and file I/O use async def + aiofiles. CPU-bound work runs in a thread pool:
await asyncio.get_event_loop().run_in_executor(None, blocking_fn)

### File header convention
Every Python module starts with:
"""
@fileoverview [Description]
@author Name <email>
@license Apache-2.0
"""
```

**Include:** Patterns that deviate from defaults, singleton access, error handling flows, async/threading rules, file naming conventions, module communication patterns.

**Skip:** Standard language conventions (PEP 8, ESLint defaults), linter-enforced rules, anything in README or CONTRIBUTING (link instead).

### Testing

Only when test setup has non-obvious requirements.

```markdown
## Testing

- `asyncio_mode = auto` in `pytest.ini` — no need for `@pytest.mark.asyncio`
- Tests marked `@pytest.mark.slow` require GPU + model. Skip with `-m "not slow"`
- Singletons are reset per-test via fixtures in `conftest.py`
```

---

## Part 2: .instructions.md Templates

### Frontmatter Template

```yaml
---
name: "Human-readable name"
description: "Use when [specific task or context]. Covers [specific topics]."
applyTo: "path/to/files/**"
---
```

**Rules:**

  - `description` is required. Front-load the use case in the first sentence
  - Always quote strings containing colons: `description: "Use when: doing X"`
  - `applyTo` uses workspace-relative glob patterns
  - One `applyTo` per file — create separate files for separate globs
  - `name` is optional but helps in diagnostics

### Example: Test Conventions

````markdown
---
name: "Test Conventions"
description: "Use when writing or modifying test files. Covers test naming, fixtures, and assertions."
applyTo: "tests/**"
---
# Test Conventions

- Name test files `test_{module}.py`
- Use fixtures from `conftest.py` — don't duplicate setup
- Use `pytest.raises` for expected exceptions

Preferred:
```python
def test_upload_rejects_invalid_format(mock_library):
    with pytest.raises(ValueError, match="unsupported format"):
        upload_file("data.xyz", mock_library)
```
````

### Example: Frontend JavaScript (applyTo-driven)

```markdown
---
name: "Frontend JS"
description: "Use when creating or modifying frontend JavaScript."
applyTo: "static/js/**"
---
# Frontend Patterns

- Escape all user-provided text before inserting into DOM
- Use `textContent` not `innerHTML` for user data
- Use event delegation on containers, not listeners on individual items
```

### Example: Window Namespace Module (applyTo-driven)

This is from a real project with two browser-first submodules sharing `window` namespaces:

```markdown
---
name: "Image Manager JS"
description: "Use when modifying Image Manager JavaScript. Covers window namespace patterns, IndexedDB persistence, and file:// compatibility."
applyTo: "image-manager/js/**"
---
# Image Manager JS Guidelines

- Publish new APIs on existing `window.app*` namespaces; route dependencies through public globals, not ES module imports
- Keep `app.js` limited to startup sequencing. Put reusable behavior in the owning module (`appCardGrid`, `appTags`, etc.)
- Treat IndexedDB as the source of truth for projects, images, and blobs. Reserve `localStorage` for lightweight UI settings only
- Keep bulk actions responsive — follow the existing small-batch async pattern
- Maintain HTML script-order assumptions: new code must work after core, api, db modules load
```

### Example: On-demand (description only, no applyTo)

```markdown
---
description: "Use when writing database migrations or modifying schemas."
---
# Migration Guidelines

- Always create reversible migrations
- Never drop columns in the same release as code removal
- Test the rollback path before merging
```

This loads when the agent determines a task involves migrations, regardless of which files are open.

---

## Part 3: Full Project Examples

### Single-Stack Project (AGENTS.md only)

When one tech stack, uniform conventions, and the file stays under ~200 lines — a single `AGENTS.md` with everything is the right call:

```markdown
# MyProject — Agents Instructions

## Project Overview

MyProject is a CLI tool for batch-processing CSV files using pandas. Python 3.11, no web framework.

## Commands

python -m myapp process input.csv output.csv
python -m pytest tests/ -v
pip install -e ".[dev]"

## Key Conventions

### Logging
Use `structlog` for all logging. Never use `print()` or `logging.getLogger()`.

### Error handling
Raise `AppError` subclasses in core code. The CLI entry point catches and formats them.
```

### Web App with Mixed Concerns (AGENTS.md + .instructions.md files)

When frontend and backend share a repo but have different conventions:

**Root AGENTS.md** — Universal rules only:

```markdown
# ProjectName — Agents Instructions

## Project Overview

ProjectName is a FastAPI REST API with a vanilla JS SPA frontend. PostgreSQL storage via SQLAlchemy 2.0 async.

## Commands

### Run
uvicorn src.main:app --reload --port 8000

### Test
pytest tests/ -x --tb=short

### Migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

## Architecture

src/
├── main.py          # App factory, middleware, lifespan
├── api/
│   ├── deps.py      # Dependency injection (DB session, auth)
│   └── v1/          # Versioned route modules
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
└── services/        # Business logic (one service per domain)

## Key Conventions

### Dependency injection
DB sessions and auth come from `api/deps.py` via FastAPI Depends(). Never create sessions directly.

### Service layer
Routes call services, services call repositories. Routes never import models directly.

See [docs/API-Reference.md](docs/API-Reference.md) for endpoint details.
```

**.github/instructions/frontend.instructions.md:**

```markdown
---
name: "Frontend JS"
description: "Use when modifying frontend JavaScript in static/js/."
applyTo: "static/js/**"
---
# Frontend JS Conventions

- Use event delegation on containers, not listeners per item
- Escape user text via `textContent`, never `innerHTML` for user data
- All API calls go through `static/js/api.js` — never use fetch directly
```

**.github/instructions/testing.instructions.md:**

```markdown
---
name: "Test Conventions"
description: "Use when writing or modifying tests."
applyTo: "tests/**"
---
# Test Conventions

- asyncio_mode = auto — no @pytest.mark.asyncio needed
- Use fixtures from conftest.py for DB sessions and mocks
- Tests marked @pytest.mark.slow require GPU — skip with -m "not slow"
```

### Multi-Module Repo (AGENTS.md + .instructions.md files)

When two distinct browser-first modules share a repo but have different namespaces and concerns:

**Root copilot-instructions.md or AGENTS.md** — Shared rules:

```markdown
## Build and Test

- Maintain compatibility with direct file:// execution from index.html
- Run npm run lint before finishing JavaScript changes
- Match the existing vanilla JavaScript style: async/await, semicolons, double quotes

## Architecture

- Two browser-first modules: image-manager/ and training-hub/
- Modules publish APIs on window and communicate through public namespaces
- Keep storage separated: IndexedDB for persistent data, localStorage for settings
- Keep the Training Hub isolated from the Image Manager database

## Conventions

- Prefer extending the relevant feature module instead of cross-cutting logic in app.js
- Use existing docs for deeper context: README.md, image-manager/docs/imagePRD.md, training-hub/docs/trainingPRD.md
```

**Per-module .instructions.md files** — Module-specific namespaces:

Each submodule gets its own `.instructions.md` with `applyTo` targeting its JS directory. These contain the specific namespace patterns, feature module names, and persistence rules unique to that submodule.

---

## Part 4: Sizing Guidelines

| File Type | Target Length | Warning Sign |
| --- | --- | --- |
| Root AGENTS.md | 50-200 lines | Over 200 = split concerns into .instructions.md |
| Subfolder AGENTS.md | 20-80 lines | Over 80 = too much detail for always-on |
| .instructions.md | 15-50 lines | Over 50 = split into multiple files |

These are soft guidelines. A 250-line AGENTS.md for a complex project with no clean split boundaries is better than artificial fragmentation.
