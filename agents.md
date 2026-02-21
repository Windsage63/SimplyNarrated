# AGENTS Guidelines for this Repository

This repository contains a Python webapp for the conversion of text to speech using local TTS via `kokoro`. The following guidelines are intended to help agent contributors understand the architecture and conventions for working within this codebase effectively.

## Primary Stack

- Python 3.12, FastAPI, Uvicorn
- Local TTS via `kokoro`
- Audio handling via `pydub`, `ffmpeg/ffprobe`, `mutagen`
- Frontend served from `static/` (vanilla JS views)
- Data persisted under `data/` (`jobs.json`, `library/`, `uploads/`)

## Repository Map

- App entrypoint: `src/main.py`
- API routes: `src/api/routes.py`
- Pipeline orchestration: `src/core/pipeline.py`
- Job lifecycle + persistence: `src/core/job_manager.py`
- Audio encode/mux/metadata: `src/core/encoder.py`
- Schemas: `src/models/schemas.py`
- Tests: `tests/`

## Environment + Run Commands (Windows-first)

- Preferred runtime uses embedded Python: `python_embedded/python.exe`
- Start app:
  - `python_embedded\python.exe -m uvicorn src.main:app --reload --port 8010`
  - or `run.bat`
- Install dependencies (manual flow):
  - install PyTorch variant first (CUDA/CPU)
  - `python_embedded\python.exe -m pip install -r requirements.txt`

## Testing Strategy

After edits, run the relevant tests.

- `python_embedded\python.exe -m pytest -q`

If ffmpeg-dependent tests fail due to local binary/path issues, report clearly and distinguish environment failure from code regression.

## Implementation Preferences

- Prefer root-cause fixes over superficial patches.
- Update docs when edits change behavior or API changes.
