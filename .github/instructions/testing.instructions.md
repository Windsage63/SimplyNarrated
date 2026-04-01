---
name: "Test Conventions"
description: "Use when writing or modifying test files. Covers fixtures, async patterns, markers, and mock audio generation."
applyTo: "tests/**"
---

# Test Conventions

## Structure

```markdown
tests/
├── conftest.py                 # Shared fixtures: temp dirs, singleton resets, mock audio
├── test_api.py                 # Endpoint integration tests (requires ffmpeg)
├── test_chunker.py             # Chunking logic
├── test_parser.py              # Text extraction and chapter detection
├── test_encoder.py             # MP3 encoding
├── test_job_manager.py         # Job queue, persistence, recovery
├── test_library.py             # Library CRUD and bookmarks
├── test_chapter_reconvert.py   # Per-chapter reconvert flow
├── test_portability.py         # ZIP export/import
├── test_schemas.py             # Pydantic model validation
├── test_tts_engine.py          # TTS engine (@pytest.mark.slow)
└── test_tts_engine_concurrency.py  # Concurrent TTS tests (@pytest.mark.slow)
```

## Async

- `asyncio_mode = auto` in `pytest.ini` — never add `@pytest.mark.asyncio` decorators
- All async test functions are plain `async def test_xxx():`

## Fixtures (from `conftest.py`)

- `tmp_data_dir`, `tmp_uploads_dir`, `tmp_library_dir` — temp filesystem, cleaned automatically
- `job_manager`, `library_manager` — singleton instances against temp dirs; globals reset after each test
- `tts_engine` — mock engine (GPU tests use real engine with `@pytest.mark.slow`)
- `async_client` — `httpx.AsyncClient` with `ASGITransport` against the FastAPI app

Always use these fixtures instead of creating your own setup. Singletons **must** be reset — the fixtures handle this by setting the module-level `_xxx` variable to `None` after yield.

## Markers

- `@pytest.mark.slow` — requires GPU + Kokoro model loaded. Skipped with `-m "not slow"`
- No other custom markers are used

## Mock Audio

Generate tiny valid audio with `scipy.io.wavfile` or `pydub.AudioSegment`. Example from conftest:

```python
audio_data = np.zeros(24000, dtype=np.float32)  # 1 second at 24kHz
```

## Naming

- Test files: `test_{module}.py` matching the source module in `src/core/`
- Test functions: `test_{behavior_being_tested}`
- Use `pytest.raises` with `match=` for expected exceptions
