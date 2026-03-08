# SimplyNarrated — Copilot Instructions

## Project Overview

SimplyNarrated is a local web application that converts books and documents (`.txt`, `.md`, `.pdf`, Gutenberg `.zip`) into MP3 audiobooks using the **Kokoro-82M** TTS model running locally on GPU. It has a FastAPI backend and a vanilla JS SPA frontend, with no external databases or cloud dependencies.

## Commands

### Run the app
```bash
# Using embedded Python (production/normal use)
python_embedded\python.exe -m uvicorn src.main:app --port 8010

# Or simply double-click run.bat
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
# PyTorch must be installed first (choose CUDA version matching your GPU):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126  # RTX 30/40
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128  # RTX 50
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu    # CPU only

pip install -r requirements.txt
```

## Python Environment
- Python 3.12 (python_embedded folder included in the repo)
- Do not use a global Python installation or virtual environment. The embedded Python is configured with all necessary dependencies and ensures consistency across development and production.

## Architecture

```
src/
├── main.py           # FastAPI app init, lifespan (startup/shutdown), static file mounting
├── api/
│   └── routes.py     # All 25+ REST endpoints (FastAPI router)
├── core/
│   ├── pipeline.py       # Main async orchestrator: parse → chunk → TTS → encode → store
│   ├── tts_engine.py     # Kokoro-82M wrapper; loads .pt voice tensors from static/voices/
│   ├── parser.py         # Extracts text from TXT/MD/PDF/ZIP; strips Gutenberg boilerplate
│   ├── chunker.py        # Splits text into ~4000-word chunks preserving chapter boundaries
│   ├── encoder.py        # WAV → MP3 conversion with ID3 tag embedding
│   ├── job_manager.py    # Async job queue with file-based persistence and restart recovery
│   ├── library.py        # File-based library: JSON metadata per book, bookmark management
│   ├── chapter_reconvert.py  # Reconvert individual chapters with different settings
│   └── portability.py    # Export/import books as ZIP archives
└── models/
    └── schemas.py        # Pydantic request/response models for all API endpoints
```

**Data layer:** No database. All persistence is file-based under `data/`:
- `data/library/{book_id}/metadata.json` — Book metadata
- `data/library/{book_id}/chapter_NN.mp3` — Audio files
- `data/library/{book_id}/chapter_NN.txt` — Editable chapter text
- `data/jobs.json` — Job ledger (survives restarts)
- `data/uploads/` — Temporary uploaded files

**Frontend:** SPA in `static/`. All vendor assets (Tailwind, fonts) are bundled in `static/vendor/` for offline use. Routes to pages are handled client-side.

**Voices:** Stored as `.pt` tensor files in `static/voices/`. Prefixed `af_`/`am_` (American female/male), `bf_`/`bm_` (British female/male). The prefix determines the G2P phoneme region passed to Kokoro.

## Key Conventions

### Singletons via module-level getters
`TTSEngine`, `JobManager`, and `LibraryManager` are initialized once at app startup (lifespan) and accessed everywhere through module-level getter functions:
```python
from src.core.job_manager import get_job_manager
job_manager = get_job_manager()
```
Tests reset these singletons via fixtures in `conftest.py` for isolation.

### FastAPI route pattern
All routes live in `src/api/routes.py` on a single `APIRouter`. Validation helpers raise `HTTPException` directly:
```python
def _validate_book_id_or_400(book_id: str) -> None:
    if not book_id: raise HTTPException(status_code=400, detail="...")

def _load_book_metadata_or_404(book_id: str) -> dict:
    metadata = library.get_book(book_id)
    if not metadata: raise HTTPException(status_code=404, detail="Book not found")
    return metadata
```

### Job activity logging
All significant job events are appended to `job.activity_log` via:
```python
job_manager._add_activity(job, "Message", "info")  # levels: info, success, warning, error
```

### Async throughout
All route handlers, pipeline stages, and file I/O use `async def` + `aiofiles`. CPU-bound TTS inference runs in a thread pool via `asyncio.get_event_loop().run_in_executor(None, ...)`.

### File header convention
Every Python module starts with:
```python
"""
@fileoverview [Description]
@author Timothy Mallory <windsage@live.com>
@license Apache-2.0
@copyright 2026 Timothy Mallory
"""
```

### Pydantic models
All API request/response schemas are in `src/models/schemas.py` using Pydantic v2 with `Field()` for descriptions and validation constraints.

### pytest configuration
`pytest.ini` sets `asyncio_mode = auto` — all async test functions run automatically without `@pytest.mark.asyncio`. Slow tests are gated with `@pytest.mark.slow`.
