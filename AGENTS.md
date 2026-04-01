# SimplyNarrated — Agents Instructions

## Project Overview

SimplyNarrated is a local web application that converts books and documents (`.txt`, `.md`, `.pdf`, Gutenberg `.zip`) into MP3 audiobooks using the **Kokoro-82M** TTS model running locally on GPU. It has a FastAPI backend and a vanilla JS SPA frontend, with no external databases or cloud dependencies. The library also supports cover management, portability export/import ZIPs, editable chapter text, and per-chapter reconversion.

## Commands

### Run the app

```bash
# Using embedded Python (production/normal use)
python_embedded\python.exe -m uvicorn src.main:app --port 8010

# Or simply double-click run.bat (starts uvicorn --reload and opens browser)
```

### Run tests

```bash
# All tests (excluding slow TTS model tests)
python_embedded\python.exe -m pytest tests/ -m "not slow"

# All tests including TTS model tests (requires GPU + model download)
python_embedded\python.exe -m pytest tests/

# Single test file
python_embedded\python.exe -m pytest tests/test_api.py

# Single test by name
python_embedded\python.exe -m pytest tests/test_chunker.py::test_function_name -v
```

Tests marked `@pytest.mark.slow` require the Kokoro-82M model loaded in memory (GPU-intensive). Skip with `-m "not slow"` during routine development.

### Install dependencies

```bash
# One-click installer handles everything (GPU detection, Python, PyTorch, deps):
install.bat

# Or manually — PyTorch first (choose CUDA version matching your GPU), then requirements:
python_embedded\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126  # RTX 30/40
python_embedded\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128  # RTX 50
python_embedded\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu    # CPU only

python_embedded\python.exe -m pip install -r requirements.txt
```

## Environment

  - Python 3.12 via `python_embedded/` directory (vendored, not a global install). Do not use a global Python or virtual environment
  - spaCy `en_core_web_sm` model is vendored under `models/en_core_web_sm/` and added to `sys.path` at runtime by `tts_engine.py`
  - All vendor assets (Tailwind CSS, Inter font, Material Symbols icons) are bundled in `static/vendor/` — zero CDN calls, fully offline

## Architecture

```markdown
src/                        # Python backend (FastAPI)
├── main.py                     # App init, lifespan (startup/shutdown), static file mounting
├── api/
│   └── routes.py               # All HTTP endpoints on a single APIRouter
├── core/
│   ├── pipeline.py             # Async orchestrator: parse → chunk → TTS → encode → store
│   ├── tts_engine.py           # Kokoro-82M wrapper; loads .pt voice tensors from static/voices/
│   ├── parser.py               # Text extraction from TXT/MD/PDF/ZIP; Gutenberg boilerplate stripping
│   ├── chunker.py              # Splits text into ~4000-word chunks preserving chapter boundaries
│   ├── encoder.py              # Raw audio → MP3 with ID3 tags
│   ├── job_manager.py          # Async job queue with file-based persistence and restart recovery
│   ├── library.py              # File-based library: JSON metadata per book, bookmark management
│   ├── chapter_reconvert.py    # Reconvert individual chapters with different settings
│   └── portability.py          # Export/import books as ZIP archives
└── models/
    └── schemas.py              # Pydantic request/response models

static/                     # Frontend SPA; detailed structure lives in .github/instructions/frontend.instructions.md

tests/                      # pytest suite; detailed structure lives in .github/instructions/testing.instructions.md

data/                       # Runtime data (no database, all file-based)
├── library/{book_id}/
│   ├── metadata.json           # Book metadata, chapter list, durations
│   ├── chapter_NN.mp3          # Audio files
│   ├── chapter_NN.txt          # Editable chapter text
│   └── bookmarks.json          # Saved playback position
├── jobs.json                   # Job ledger (survives restarts)
└── uploads/                    # Temporary uploaded files

docs/                       # Project documentation
├── API-Reference.md            # Full endpoint reference with request/response examples
├── Landing-Page-Creative-Brief.md
└── stitch/                     # Design mockups (5 screens)

scripts/                    # Manual validation and utility scripts
```

**Voices:** Stored as `.pt` tensor files in `static/voices/`. Prefixed `af_`/`am_` (American female/male), `bf_`/`bm_` (British female/male). The prefix determines the G2P phoneme region passed to Kokoro.

## Key Conventions

### File header convention

Every Python, JavaScript, or HTML file starts with a standard Apache 2.0 license header as shown in the `license-headers` skill.

### Singletons via module-level getters

`TTSEngine`, `JobManager`, and `LibraryManager` are initialized once at app startup (lifespan) and accessed everywhere through module-level getter functions:

```python
from src.core.job_manager import get_job_manager
job_manager = get_job_manager()
```

Tests reset these singletons via fixtures in `conftest.py` for isolation.

### Async throughout

All route handlers, pipeline stages, and file I/O use `async def` + `aiofiles`. CPU-bound TTS inference runs in a thread pool via `asyncio.get_event_loop().run_in_executor(None, ...)`.

### API docs

See [docs/API-Reference.md](docs/API-Reference.md) for all endpoints with request/response examples.
