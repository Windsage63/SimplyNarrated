# Phase 1 Implementation Checklist

Source plan: `plans/tts_multi_model_plan.md`
Goal: land a Kokoro-only model registry, remove the legacy audio-settings contract, and keep generation/reconvert behavior working for the supported path.

## Scope

  - Add a model-aware TTS manager abstraction with only `kokoro` registered.
  - Remove upload-time audio settings from frontend, API schemas, pipeline config, and reconvert requests.
  - Persist `model` alongside `voice` in book metadata.
  - Expose model and voice through API responses needed by the frontend.
  - Add model selection UI plumbing even though Phase 1 only exposes one model.
  - Update tests and fixtures to the new request/config contract.

## File Checklist

### `src/core/tts_engine.py`

  - [x] Introduce `BaseTTSModel` and convert current `TTSEngine` into `KokoroTTSModel`.
  - [x] Add `TTSModelManager` with registry, `get_active_model()`, `switch_model()`, and `get_available_model_names()`.
  - [x] Keep Kokoro preload and sample generation behavior unchanged.
  - [x] Replace global engine accessor with manager accessor.

### `src/models/schemas.py`

  - [x] Add `model` to `GenerateRequest`.
  - [x] Remove `speed`, `quality`, `format`, and footnote-removal request fields from generation/reconvert request models.
  - [x] Add `model` to `VoiceInfo`.
  - [x] Add `model` and `voice` to `BookInfo`.

### `src/core/library.py`

  - [x] Add `model` to `BookMetadata`.
  - [x] Map stored `model` and `voice` into `BookInfo` responses.
  - [x] Default missing book metadata model to `kokoro` for legacy books.

### `src/core/pipeline.py`

  - [x] Use `get_tts_manager()` instead of `get_tts_engine()`.
  - [x] Remove legacy audio-settings config handling.
  - [x] Hardcode SD encoder settings.
  - [x] Save `model` in generated book metadata.

### `src/core/chapter_reconvert.py`

  - [x] Read `model` and `voice` from book metadata.
  - [x] Switch the active model before synthesis.
  - [x] Remove speed/quality/format overrides from the reconvert flow.
  - [x] Preserve metadata updates for reconverted chapters under the new model-aware contract.

### `src/api/routes.py`

  - [x] Replace static voice list usage with manager-backed lookups.
  - [x] Add `GET /models`.
  - [x] Add `POST /models/switch`.
  - [x] Make `GET /voices` model-aware.
  - [x] Make voice preview caching model-aware.
  - [x] Validate generate/reconvert requests against the selected model's voices.

### `static/js/app.js`

  - [x] Add `selectedModel` state.
  - [x] Reset `selectedVoice` default to empty.
  - [x] Remove `audioSettings` fields that no longer exist.
  - [x] Add model-aware API helpers for models, voices, preview, and generate.

### `static/js/views/upload.js`

  - [x] Add model dropdown UI.
  - [x] Remove the Audio Settings section and handlers.
  - [x] Load voices for the selected model.
  - [x] Require file + model + voice before enabling conversion.

### `static/js/views/player.js`

  - [x] Use book `model` and `voice` for reconvert requests.

### `install.bat`

  - [x] Switch preload call to the new manager entry point.
  - [x] Keep Phase 1 install behavior Kokoro-only.

### Tests

  - [x] Update request fixtures and direct `process_book()` configs.
  - [x] Update fake TTS doubles to the new `generate_speech()` signature.
  - [x] Add or update coverage for `GET /models`, model-aware voices, and legacy metadata defaulting.
  - [x] Rerun narrow API/pipeline/reconvert tests before broader validation.

## Execution Order

1. Backend manager + schema + metadata plumbing.
2. API route migration off static voices.
3. Frontend model-selection and audio-settings removal.
4. Test fixture updates.
5. Targeted validation, then wider validation if needed.

## Validation Results

  - [x] `tests/test_pipeline_pdf.py`
  - [x] `tests/test_chapter_reconvert_api.py`
  - [x] `tests/test_txt_path.py`
  - [x] `tests/test_frontend_smoke.py`
  - [ ] Live-marker tests were updated for the new contract but not run in this pass.
