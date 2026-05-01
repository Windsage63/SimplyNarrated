# SimplyNarrated Code Review - 2026-04-30

## Summary

SimplyNarrated has a clear backend split between API routes, job orchestration, import/parsing, rendering, and library persistence, and the test suite already covers several important backend contracts. The highest-value improvements are frontend output escaping, tighter ZIP resource limits, lifecycle cleanup for polling, and reducing duplicated frontend/backend helpers.

Finding count: 1 Blocker, 6 Major, 7 Minor, 1 Nit.

## Critical Issues (Security, Correctness, Performance)

  - **Blocker** Stored metadata can execute as HTML/JS in the frontend.
    - Evidence: user- and archive-derived metadata is interpolated into template strings assigned through `innerHTML`, including dashboard titles and inline handlers in `static/js/views/dashboard.js:212`, `static/js/views/dashboard.js:225`, and `static/js/views/dashboard.js:246`; chapter titles render the same way in `static/js/views/player.js:335` and `static/js/views/player.js:355`; job activity messages render through `innerHTML` in `static/js/views/progress.js:109` and `static/js/views/progress.js:130`.
    - Why it matters: book title, author, chapter title, and activity text can originate from uploaded documents, imported archives, or metadata edits. A crafted title such as `<img src=x onerror="fetch('/api/book/...',{method:'DELETE'})">` would run in the app origin when the dashboard renders.
    - Suggested improvement: render untrusted values with `textContent`/DOM builders, or add a small `escapeHtml()` helper and use it consistently for template interpolation. Avoid putting untrusted values inside inline `onclick` strings; bind events with `addEventListener` and `data-*` attributes.

  - **Major** Gutenberg ZIP parsing has no uncompressed-size or member-count guard.
    - Evidence: upload limits only the compressed file to 50 MB in `src/api/routes.py:70` and `src/api/routes.py:206`, but generation later reads candidate HTML members fully into memory in `src/core/gutenberg_parser.py:88` and `src/core/gutenberg_parser.py:96`; cover extraction also reads the selected image fully in `src/core/gutenberg_parser.py:415` and `src/core/gutenberg_parser.py:441`.
    - Why it matters: a small compressed ZIP can contain huge uncompressed HTML/image members and exhaust memory or disk during generation. The portability importer already has stronger limits (`MAX_ARCHIVE_MEMBERS`, `MAX_ARCHIVE_UNCOMPRESSED_SIZE`) in `src/core/portability.py`, but the Gutenberg source path does not reuse them.
    - Suggested improvement: add Gutenberg ZIP limits before reading members: max member count, max total uncompressed bytes, max per-HTML bytes, and max cover image bytes. Reject oversized archives early with a clear job failure message.

  - **Major** Cover uploads trust client-provided MIME type and extension.
    - Evidence: `upload_cover()` accepts based on `file.content_type` and filename extension in `src/api/routes.py:737` and `src/api/routes.py:744`, then writes the bytes directly in `src/api/routes.py:753` and `src/api/routes.py:773`.
    - Why it matters: clients control multipart content types. This can store invalid image bytes as `cover.jpg`/`cover.png`, break browser rendering, and embed bad cover payloads into MP3 tags through `retag_book_mp3_files()`.
    - Suggested improvement: verify image magic bytes or decode with Pillow before saving; normalize output by re-encoding to JPEG/PNG. Keep the existing 5 MB cap.

## Logic & Edge Cases

  - **Major** Progress polling intervals leak when navigating away from the progress view.
    - Evidence: `initProgressView()` always starts `setInterval(pollStatus, 5000)` in `static/js/views/progress.js:75` and `static/js/views/progress.js:78`; intervals are cleared only on completion/failure/cancel in `static/js/views/progress.js:139`, `static/js/views/progress.js:155`, and `static/js/views/progress.js:170`. `showView()` only tears down the player view in `static/js/app.js:259` through `static/js/app.js:266`.
    - Why it matters: if the user leaves the progress view manually, the poller keeps running, can create duplicate intervals on re-entry, and will try to update DOM elements that no longer exist.
    - Suggested improvement: add `teardownProgressView()` that clears the interval and call it from `showView()` when leaving progress. Also clear any existing interval before assigning a new one in `initProgressView()`.

  - **Major** Per-chapter reconversion can race when concurrent jobs are enabled.
    - Evidence: concurrency is configurable through `MAX_CONCURRENT_JOBS` in `src/core/job_manager.py:368` and `src/core/job_manager.py:369`; reconvert requests create independent jobs in `src/api/routes.py:622` and queue them in `src/api/routes.py:641`; each job writes a temp MP3 and replaces the same chapter file in `src/core/chapter_reconvert.py:145`, `src/core/chapter_reconvert.py:237`, and updates the same metadata file in `src/core/chapter_reconvert.py:245`.
    - Why it matters: two reconversions for the same book/chapter can complete out of order. The older job may overwrite newer audio or metadata, especially if a user clicks `Save + Reconvert` repeatedly or multiple browser tabs are open.
    - Suggested improvement: maintain an active `(book_id, chapter_number)` reconvert registry, reject/return the existing job while one is active, or add a per-chapter async lock around the replace + metadata update path.

  - **Minor** Cancellation is cooperative only between chapter steps, not inside TTS/encoding work.
    - Evidence: `process_book()` checks `job.status == JobStatus.CANCELLED` only at the top of each chapter loop in `src/core/pipeline.py:187`; long TTS and encoding operations are dispatched via `_run_blocking()` in `src/core/pipeline.py:201` and `src/core/pipeline.py:214`.
    - Why it matters: cancelling during a long chapter can mark the task cancelled while the worker thread continues doing expensive TTS/encoding work until that blocking call returns.
    - Suggested improvement: expose cancel state to the renderer/TTS layer if possible, or update UI copy to say cancellation stops after the current chapter. At minimum, re-check cancellation immediately after each blocking call and before writing final artifacts.

## Simplification & Minimalism

  - **Minor** Frontend fetch/error handling is duplicated and inconsistent.
    - Evidence: `static/js/app.js` repeats `response.ok` parsing in many methods, for example `static/js/app.js:57`, `static/js/app.js:81`, `static/js/app.js:143`, and `static/js/app.js:205`; `player.js` bypasses the shared API client with direct `fetch()` calls in `static/js/views/player.js:291`, `static/js/views/player.js:584`, and `static/js/views/player.js:645`.
    - Suggested improvement: add `api.request(path, options, fallbackMessage)` and route all frontend API calls through it. This will simplify error handling, make response parsing consistent, and centralize future concerns such as timeouts.

  - **Minor** TXT and Gutenberg parsers duplicate chapter splitting logic.
    - Evidence: both `src/core/text_parser.py` and `src/core/gutenberg_parser.py` define similar word-budget splitting and chapter finalization flows, including `_split_blocks_by_word_budget()` in `src/core/text_parser.py` and `src/core/gutenberg_parser.py`.
    - Suggested improvement: extract a small shared `chapter_splitter` helper that accepts blocks, max words, and a title factory. Keep parser-specific cleanup local, but share the budget splitting mechanics.

  - **Minor** Job persistence rewrites the whole ledger synchronously on progress updates.
    - Evidence: `_persist_jobs()` writes the full `jobs.json` payload in `src/core/job_manager.py:136` through `src/core/job_manager.py:141`; `update_progress()` calls it for each progress message in `src/core/job_manager.py:222` and `src/core/job_manager.py:236`.
    - Why it matters: retention helps, but the event loop still does synchronous full-file writes during conversion progress. This can add UI latency on slower disks or large ledgers.
    - Suggested improvement: debounce persistence, write only on meaningful progress deltas, or move persistence to an async/background flush queue with atomic replace.

## Elegance & Idiomatic Enhancements

  - **Minor** Voice selection re-renders the whole grid and introspects handler source text.
    - Evidence: `selectVoice()` toggles selection by checking `card.onclick.toString().includes(voiceId)` in `static/js/views/upload.js:268` through `static/js/views/upload.js:273`, then calls `loadVoices()` to re-render in `static/js/views/upload.js:276`.
    - Suggested improvement: store `data-voice-id` on cards and toggle based on that value. Avoid full re-fetch/re-render for a single selection state change.

  - **Minor** Inline event handlers make the frontend harder to escape and refactor.
    - Evidence: route rendering and view templates use `onclick` attributes broadly, such as `static/index.html:245`, `static/js/views/dashboard.js:216`, and `static/js/views/player.js:338`.
    - Suggested improvement: prefer event delegation on stable containers. This pairs naturally with escaping fixes because untrusted data no longer has to be serialized into executable attribute strings.

  - **Nit** The API route module has become a broad catch-all.
    - Evidence: `src/api/routes.py` contains upload/generation, status, voice samples, library import/export, audio/text streaming, bookmarks, metadata, cover upload, and deletion.
    - Suggested improvement: split routes by domain (`jobs.py`, `library.py`, `media.py`, `voices.py`) once the current feature work settles. Keep schemas shared.

## Documentation & Testability

  - **Major** There are no regression tests for frontend escaping or progress lifecycle cleanup.
    - Evidence: current frontend tests are static smoke assertions in `tests/test_frontend_smoke.py`; they check served assets and text presence, but not DOM rendering safety or timer teardown.
    - Suggested improvement: add a small browser or DOM-level test that renders a book titled with HTML and asserts no script/handler executes and the visible text is escaped. Add a timer lifecycle test by navigating progress -> dashboard -> progress and asserting one active interval.

  - **Major** ZIP resource-limit behavior is not covered by tests.
    - Evidence: `tests/test_gutenberg_parser.py` covers normal parsing, invalid ZIPs, unsafe paths, and fallback splitting, but not uncompressed-size or member-count limits.
    - Suggested improvement: add parser tests for too many members, huge uncompressed HTML metadata, oversized cover assets, and duplicate/unsafe ZIP members. Mirror the portability importer's guard style.

  - **Minor** Test execution needs a documented embedded-Python command.
    - Evidence: global `python` and `pytest` were not available in this workspace; using `.\python_embedded\python.exe -m pytest ...` is the expected path. Pytest also attempted to write temp/cache outside writable areas unless explicitly redirected.
    - Suggested improvement: document a Windows command such as `.\python_embedded\python.exe -m pytest -m "not live_tts" -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp` in the README or a contributor note.

## Positive Observations

  - The backend uses typed request/response schemas and validates key user-controlled identifiers before path construction.
  - Blocking TTS, encoding, metadata retagging, and document conversion are generally offloaded from async request handlers, which is the right direction for a local FastAPI app.
  - Portability archive import is much more defensive than the Gutenberg ZIP path: it checks member count, total uncompressed size, unsafe paths, duplicate entries, manifest type, and schema version.
  - Metadata writes use lock-protected atomic replacement in `src/core/metadata_store.py`, which is a solid foundation for file-based persistence.
  - The reconvert workflow has thoughtful Windows file-lock handling through temp output and retrying `os.replace()`.

## Verification Notes

  - Used the embedded interpreter: `.\python_embedded\python.exe`.
  - `.\python_embedded\python.exe -m pytest -m "not live_tts"` initially failed because pytest tried to create temp/cache files outside accessible paths.
  - Re-running with `TEMP`, `TMP`, `cache_dir`, and `--basetemp` redirected into `C:\tmp` allowed collection and one non-API test to pass, but API-backed tests still reported errors and the process timed out before pytest printed full tracebacks. I did not count that as an application failure without a complete traceback.

## Prioritized Findings Summary

| # | Severity | Section | Finding | Effort |
| --- | --- | --- | --- | --- |
| 1 | **Blocker** | Critical Issues | Stored metadata can execute as HTML/JS in frontend templates | Med |
| 2 | **Major** | Critical Issues | Gutenberg ZIP parser lacks uncompressed-size/member-count guards | Med |
| 3 | **Major** | Critical Issues | Cover upload trusts MIME and extension without image verification | Low |
| 4 | **Major** | Logic & Edge Cases | Progress polling intervals leak across view navigation | Low |
| 5 | **Major** | Logic & Edge Cases | Concurrent chapter reconversions can overwrite each other | Med |
| 6 | **Major** | Documentation & Testability | No regression tests for frontend escaping or timer lifecycle | Med |
| 7 | **Major** | Documentation & Testability | ZIP resource-limit behavior lacks tests | Low |
| 8 | **Minor** | Logic & Edge Cases | Cancellation does not interrupt in-flight TTS/encoding work | Med |
| 9 | **Minor** | Simplification | Frontend API error handling is duplicated and inconsistent | Low |
| 10 | **Minor** | Simplification | TXT/Gutenberg chapter splitting logic is duplicated | Med |
| 11 | **Minor** | Simplification | Job persistence does synchronous full-ledger rewrites on progress | Med |
| 12 | **Minor** | Elegance | Voice selection re-renders and introspects handler source | Low |
| 13 | **Minor** | Elegance | Inline handlers make escaping/refactoring harder | Med |
| 14 | **Minor** | Documentation & Testability | Embedded-Python test command should be documented | Low |
| 15 | **Nit** | Elegance | API routes module is doing too many unrelated jobs | Med |
