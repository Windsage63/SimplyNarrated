# SimplyNarrated — Code Review Report

**Date:** 2026-03-29  
**Scope:** Full backend source (`src/`), test suite (`tests/`), schemas, and supporting modules  
**Reviewer:** GitHub Copilot (automated review)

> **Resolution Status (2026-03-30):** All 19 findings in this report have been resolved. The corrections were implemented per the companion PRD (`plans/prd_code_review_corrections_2026-03-30.md`). All 5 Major, 9 Minor, and 5 Nit items are addressed. The test suite now contains **164 non-slow tests** covering the new `test_chapter_reconvert.py`, `test_portability.py`, and PDF parsing additions.

---

## Summary

SimplyNarrated is a well-structured local audiobook converter with clean separation of concerns, thorough input validation, and a solid test suite (~185+ tests). The codebase follows its own documented conventions consistently. The main areas of concern are: (1) **unvalidated `narrator_voice` input flows to the TTS engine** allowing arbitrary voice IDs through the generation pipeline, (2) **synchronous blocking I/O inside `async def` functions** that can stall the event loop under load, (3) **internal exception details leaking to API clients** in error responses, and (4) **excessive file-system persistence** on every activity log entry during chapter generation. No Blockers were found; the application is functional and safe for its local-use design.

**Finding counts:** 0 Blocker, 5 Major, 9 Minor, 5 Nit

---

## Critical Issues (Security, Correctness, Performance)

  - **[Major]** `narrator_voice` is not validated against `PRESET_VOICES` in the generation pipeline. A user can submit any string as `narrator_voice` in the `GenerateRequest`, and it passes unchecked through `routes.py` → `pipeline.py` → `tts_engine.generate_speech()`. If the voice ID doesn't match a local `.pt` file, Kokoro attempts a HuggingFace download — unintended for an offline-first app. The `voice-sample` endpoint validates against `AVAILABLE_VOICES`, but the generation and reconvert endpoints do not.
    - Evidence: [routes.py](src/api/routes.py#L234) passes `request.narrator_voice` verbatim into config; [pipeline.py](src/core/pipeline.py#L144) uses it directly; [tts_engine.py](src/core/tts_engine.py#L124) `_resolve_voice()` falls back to the bare ID string if no `.pt` file exists.
    - Suggested fix: Add a validation check in `routes.py` for `/generate` and `/reconvert` endpoints:

    ```python
    valid_voice_ids = {v.id for v in AVAILABLE_VOICES}
    if request.narrator_voice not in valid_voice_ids:
        raise HTTPException(status_code=400, detail="Invalid narrator voice")
    ```

  - **[Major]** Internal exception messages are exposed to API clients. The voice-sample endpoint returns `f"Failed to generate sample: {e}"` in an HTTP 500 response, which may leak stack trace fragments, file paths, or internal state.
    - Evidence: [routes.py](src/api/routes.py#L374): `raise HTTPException(status_code=500, detail=f"Failed to generate sample: {e}")`
    - Suggested fix: Return a generic error message; log the details server-side:

    ```python
    raise HTTPException(status_code=500, detail="Failed to generate voice sample")
    ```

  - **[Major]** `_persist_jobs()` writes the full jobs JSON file synchronously to disk on **every** activity log entry. During chapter generation, this is called multiple times per chapter (progress update, activity log, completion), causing heavy synchronous I/O that blocks the event loop. For a 50-chapter book, this could mean 150+ file writes.
    - Evidence: [job_manager.py](src/core/job_manager.py#L194) — `_add_activity()` calls `_persist_jobs()` unconditionally. `_persist_jobs()` at [line 133](src/core/job_manager.py#L133) serializes all jobs and writes synchronously.
    - Suggested fix: Debounce persistence (e.g. persist at most once per N seconds or batch at the end of each phase), or make `_persist_jobs` async with `aiofiles`.

  - **[Major]** `parse_file()` is a synchronous, potentially heavy call (PDF parsing, ZIP extraction) invoked directly inside the `async def process_book()` coroutine without `run_in_executor`. While `asyncio.sleep(0.1)` is called before it, parsing a large PDF still blocks the event loop.
    - Evidence: [pipeline.py](src/core/pipeline.py#L76): `document = parse_file(job.file_path)` — called directly, not via executor.
    - Suggested fix:

    ```python
    loop = asyncio.get_running_loop()
    document = await loop.run_in_executor(None, parse_file, job.file_path)
    ```

  - **[Major]** `_load_book_metadata_or_404()` performs synchronous file I/O (`open()`, `json.load()`) and is called from multiple `async def` route handlers (bookmark, cover, chapter text, reconvert, update metadata, delete). Under concurrent requests this blocks the event loop.
    - Evidence: [routes.py](src/api/routes.py#L98-L101): synchronous `open()` + `json.load()` inside a helper called from async endpoints.
    - Suggested fix: Convert to async using `aiofiles`:

    ```python
    async def _load_book_metadata_or_404(book_dir: str) -> dict:
        metadata_path = os.path.join(book_dir, "metadata.json")
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Book not found")
        async with aiofiles.open(metadata_path, "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    ```

---

## Logic & Edge Cases

  - **[Minor]** `_estimate_chapters()` in `routes.py` imports `zipfile` and `io` inside the function body on every call for ZIP uploads. These are lightweight stdlib modules but the local import pattern is unusual and the function catches all exceptions silently, returning a fallback — which is fine for estimation but could mask real errors.
    - Evidence: [routes.py](src/api/routes.py#L123-L137)
    - Suggestion: Move the imports to the top of the file for clarity. The broad `except Exception: pass` is acceptable for an estimation-only function.

  - **[Minor]** `chunk_text()` can enter an infinite loop if `_find_break_point()` returns an empty string (all whitespace after `.strip()`). When `actual_words` is 0 and `current_pos < len(words)`, the loop never advances.
    - Evidence: [chunker.py](src/core/chunker.py#L85-L100): `actual_words = len(chunk_text.split())` — if this is 0, `current_pos += 0` forever.
    - Suggested fix: Add a guard:

    ```python
    if actual_words == 0:
        actual_words = len(chunk_words)
        chunk_text = " ".join(chunk_words)
    ```

  - **[Minor]** `flush_bucket()` in `chunk_chapters()` captures and mutates outer-scope lists (`current_bucket_text`, `current_bucket_titles`) as a closure, but `current_bucket_word_count` is reassigned via `= flush_bucket()`. This pattern works but is fragile — forgetting the reassignment leads to a stale bucket count.
    - Evidence: [chunker.py](src/core/chunker.py#L147-L170)
    - Suggestion: Make the bucket an explicit data structure (dict or list) so all three pieces of state are co-located and cleared together.

  - **[Minor]** `extract_cover_image()` for ZIP files accepts `.gif` images but the cover save logic only branches on `.jpg`/`.jpeg`/`.png`, defaulting to `cover.png` for GIF. This produces a PNG-named file containing GIF data.
    - Evidence: [parser.py](src/core/parser.py#L449-L460): GIF members are found but the filename becomes `cover.png`.
    - Suggested fix: Either exclude `.gif` from the filter or add a GIF branch that re-encodes or names appropriately.

  - **[Minor]** The chapter reconvert metadata update at the end of `process_chapter_reconvert_job` reads and writes `metadata.json` without any file locking. If two reconvert jobs for different chapters of the same book run concurrently, the last writer wins and the first writer's duration update is lost.
    - Evidence: [chapter_reconvert.py](src/core/chapter_reconvert.py#L110-L242) — reads metadata at the start, writes at the end, no locking.
    - Mitigation: The `JobManager` semaphore (`max_concurrent_jobs=1`) serializes jobs by default. Document this dependency, or add file-level locking to be resilient if concurrency is increased.

  - **[Minor]** `_replace_with_retry()` in `chapter_reconvert.py` uses `time.sleep()` (blocking) inside an `async def` coroutine. Although the retry scenario is rare, blocking sleep stalls the event loop for up to 3 seconds total.
    - Evidence: [chapter_reconvert.py](src/core/chapter_reconvert.py#L76): `time.sleep(retry_delay_seconds)`.
    - Suggested fix: Run `_replace_with_retry` in an executor, or replace `time.sleep` with `await asyncio.sleep()` and make the function async.

---

## Simplification & Minimalism

  - **[Minor]** `encoder.py` always exports as `format="mp3"` regardless of the `settings.format` value passed in. The `AudioFormat` enum only contains `MP3` and reconvert explicitly checks `format != "mp3"`. The `EncoderSettings.format` and `AudioFormat` fields add unused abstraction that may confuse future contributors.
    - Evidence: [encoder.py](src/core/encoder.py#L109): `audio_segment.export(..., format="mp3", ...)` hard-codes `"mp3"`.
    - Suggestion: Either remove the `format` field from `EncoderSettings`/`AudioFormat` or actually use it in `encode_audio()`. Since WAV support is not planned, simplifying to MP3-only is cleaner.

  - **[Nit]** `_configure_ffmpeg_paths()` is called on every `encode_audio()` invocation. `static_ffmpeg.add_paths()` is idempotent but incurs import overhead each time.
    - Evidence: [encoder.py](src/core/encoder.py#L81)
    - Suggestion: Call it once at module load time or at app startup, similar to `main.py`'s existing `static_ffmpeg.add_paths()` call.

  - **[Nit]** `pipeline.py` opens metadata JSON for writing without `encoding="utf-8"`, while all other JSON writes in the codebase specify it.
    - Evidence: [pipeline.py](src/core/pipeline.py#L250): `with open(metadata_path, "w") as f:` — missing `encoding="utf-8"`.
    - Suggested fix: Add `encoding="utf-8"` for consistency and Windows correctness.

---

## Elegance & Idiomatic Enhancements

  - **[Nit]** `_add_activity()` calls `_persist_jobs()` synchronously on every log append. A more idiomatic pattern for an async app would be to mark jobs as dirty and flush in a batch at the end of each major phase.
    - (This overlaps with the Major performance finding above; the pattern suggestion is included for completeness.)

  - **[Minor]** Duplicate ffmpeg path setup: `main.py` calls `static_ffmpeg.add_paths()` at import time, and `encoder.py` calls `_configure_ffmpeg_paths()` before every encode. Only one of these is needed.
    - Evidence: [main.py](src/main.py#L33-L36) and [encoder.py](src/core/encoder.py#L36-L41)
    - Suggestion: Keep it only in `main.py` (or only in `encoder.py`) — not both.

  - **[Nit]** `logger.info(f"Generating voice sample for {voice_id}: '{quote[:50]}...'")` uses an f-string inside the logger call. Prefer `logger.info("Generating voice sample for %s: '%.50s...'", voice_id, quote)` to defer string formatting when the log level is disabled.
    - Evidence: [routes.py](src/api/routes.py#L340), [routes.py](src/api/routes.py#L373)

---

## Documentation & Testability

  - **[Minor]** `chapter_reconvert.py` and `portability.py` have **no direct unit tests**. They're only tested indirectly through API integration tests. This makes it harder to isolate regressions.
    - Evidence: No `test_chapter_reconvert.py` or `test_portability.py` exist.
    - Suggestion: Add focused unit tests for `_replace_with_retry`, `_format_total_duration_from_chapters`, `sanitize_filename_component`, `_normalize_book_metadata`, export/import roundtrip at the function level.

  - **[Nit]** PDF parsing has no test coverage. `parse_pdf()` is listed in the parser dispatch table but no test fixtures or tests exercise it.
    - Evidence: No PDF fixture in `conftest.py`; `test_parser.py` has no `TestParsePdf` class.
    - Suggestion: Add a small test PDF fixture and tests for title/author extraction and chapter detection.

---

## Positive Observations

  - **Path traversal prevention** is handled well: `BOOK_ID_PATTERN` validates UUIDs, `_safe_zip_member()` rejects `..` components, and `_is_safe_archive_member()` in portability catches drive letters and absolute paths.
  - **Singleton isolation in tests** is excellent — fixtures properly reset module-level globals, preventing cross-test contamination.
  - **File-based persistence** is a great design for a local app: no database dependencies, simple JSON files, and the restart-recovery logic in `JobManager` marks interrupted jobs as failed.
  - **Voice `.pt` files are vendored** — no runtime downloads needed for voices, and the installer preloads the Kokoro model and both English pipelines.
  - **Consistent code style**: file headers, naming conventions, and the `_validate_*_or_400` pattern in routes are applied uniformly.
  - **ZIP bomb protection**: both the Gutenberg parser and portability importer enforce member count and uncompressed size limits.
  - **ID3 metadata embedding** is thorough — title, album, artist, track number, and cover art are all tagged on generated MP3s.
  - **Portability export/import** is well-designed with manifest versioning, safe filename sanitization (including Windows reserved names), and clean ID remapping on conflict.

---

## Prioritized Findings Summary

| # | Severity | Section | Finding | Effort | Status |
| - | -------- | ------- | ------- | ------ | ------ |
| 1 | **Major** | Critical Issues | `narrator_voice` not validated against preset list in `/generate` and `/reconvert` | Low | ✅ Resolved |
| 2 | **Major** | Critical Issues | Internal exception details leaked in voice-sample 500 response | Low | ✅ Resolved |
| 3 | **Major** | Critical Issues | `_persist_jobs()` called synchronously on every activity log entry during generation | Med | ✅ Resolved |
| 4 | **Major** | Critical Issues | `parse_file()` blocks event loop in `async def process_book()` | Low | ✅ Resolved |
| 5 | **Major** | Critical Issues | `_load_book_metadata_or_404()` synchronous I/O in async route handlers | Med | ✅ Resolved |
| 6 | **Minor** | Logic & Edge Cases | `chunk_text()` potential infinite loop when break point yields empty text | Low | ✅ Resolved |
| 7 | **Minor** | Logic & Edge Cases | GIF cover images saved with `.png` extension in ZIP extraction | Low | ✅ Resolved |
| 8 | **Minor** | Logic & Edge Cases | Chapter reconvert metadata write has no file locking (relies on semaphore) | Med | ✅ Documented |
| 9 | **Minor** | Logic & Edge Cases | `_replace_with_retry()` uses blocking `time.sleep()` in async context | Low | ✅ Resolved |
| 10 | **Minor** | Logic & Edge Cases | `flush_bucket()` mutation pattern in `chunk_chapters` is fragile | Low | ✅ Resolved |
| 11 | **Minor** | Logic & Edge Cases | `_estimate_chapters()` local imports `zipfile`/`io` inside function body | Low | ✅ Resolved |
| 12 | **Minor** | Simplification | `EncoderSettings.format` / `AudioFormat` unused since MP3 is hard-coded | Low | ✅ Resolved |
| 13 | **Minor** | Elegance | Duplicate `static_ffmpeg.add_paths()` in both `main.py` and `encoder.py` | Low | ✅ Resolved |
| 14 | **Minor** | Documentation | No direct unit tests for `chapter_reconvert.py` or `portability.py` | Med | ✅ Resolved |
| 15 | **Nit** | Simplification | `_configure_ffmpeg_paths()` called on every encode call | Low | ✅ Resolved |
| 16 | **Nit** | Simplification | Missing `encoding="utf-8"` on metadata JSON write in `pipeline.py` | Low | ✅ Resolved |
| 17 | **Nit** | Elegance | f-strings in logger calls should use `%s`-style formatting | Low | ✅ Resolved |
| 18 | **Nit** | Documentation | No PDF parsing test coverage | Med | ✅ Resolved |
| 19 | **Nit** | Elegance | `_add_activity` persistence pattern (overlaps with #3) | Med | ✅ Resolved |
