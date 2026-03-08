# SimplyNarrated Code Review Report

Date: 2026-03-08
Scope: Entire repository review with emphasis on correctness, security, concurrency, file handling, frontend state flow, and testability.
Validation performed: `python_embedded\python.exe -m pytest tests/ -m "not slow" -q` -> 181 passed, 13 deselected.

## Summary

The project is in solid shape overall: the non-slow test suite is green, the API surface is reasonably well covered, and the portability and chapter-reconvert workflows are more disciplined than a typical file-based app of this size. The main concerns are concentrated in a few places where file handling or concurrency assumptions are too loose: markdown cover extraction can read arbitrary local files, TTS pipeline initialization is not synchronized, and the newly embedded MP3 metadata can drift out of sync after metadata or cover edits.

## Critical Issues (Logic, Security, Performance)

### Major: Markdown cover extraction can copy arbitrary local files outside the uploaded document tree

- Issue description
  The markdown cover extraction path resolves any local image reference and only checks whether the resulting path exists. A crafted markdown file can reference `..\..\...` paths outside the uploaded document directory, causing the application to copy arbitrary local JPG or PNG files into the library and then serve them via the cover endpoint.
- Evidence
  - `src/core/parser.py:392` claims a security boundary exists.
  - `src/core/parser.py:393` only checks `os.path.isfile(img_path)`.
  - `src/core/parser.py:406` copies the resolved file with `shutil.copy2(img_path, cover_path)`.
- Suggested improvement
  Minimal fix: require the resolved path to stay under the markdown file's parent directory before copying.

  Example:

  ```python
  source_dir = os.path.dirname(os.path.abspath(file_path))
  img_path = os.path.normpath(os.path.join(source_dir, img_ref))

  if os.path.commonpath([source_dir, img_path]) != source_dir:
      return None
  if not os.path.isfile(img_path):
      return None
  ```

  This closes the local-file exfiltration path while preserving legitimate relative image references.

### Major: TTS lazy initialization is not concurrency-safe and can double-load the model under parallel requests

- Issue description
  `TTSEngine` mutates `_pipelines`, `_shared_model`, and `_initialized` without any locking. Two requests entering `generate_speech()` at the same time can both pass the `if not self._initialized` or `if lang_code not in self._pipelines` checks and initialize Kokoro twice. On GPU hardware, that can mean redundant model loads, memory spikes, or inconsistent pipeline state.
- Evidence
  - `src/core/tts_engine.py:120` checks `if lang_code not in self._pipelines:` without synchronization.
  - `src/core/tts_engine.py:127` branches on `if self._shared_model is None:` without synchronization.
  - `src/core/tts_engine.py:143` stores `self._pipelines[lang_code] = pipeline` after model creation.
  - `src/core/tts_engine.py:180` still performs unsynchronized `if not self._initialized:` before calling `initialize()`.
- Suggested improvement
  Add a process-wide lock around initialization and pipeline creation.

  Example:

  ```python
  import threading

  class TTSEngine:
      def __init__(self, device: Optional[str] = None):
          ...
          self._init_lock = threading.Lock()

      def _get_pipeline(self, voice_id: str):
          lang_code = self._lang_code_for_voice(voice_id)
          with self._init_lock:
              if lang_code in self._pipelines:
                  return self._pipelines[lang_code]
              ...
  ```

  That keeps the singletons single, which matters most in the voice sample endpoint and any future increase in concurrent job count.

### Major: Editing book metadata or uploading a new cover does not retag existing chapter MP3 files

- Issue description
  MP3 metadata is written only during initial generation and chapter reconversion. Later metadata edits update `metadata.json` only, and cover uploads update the cover file plus `cover_url` only. Generic music players will therefore continue showing the old album title, old artist, or old artwork until each chapter is individually regenerated.
- Evidence
  - `src/core/pipeline.py:188` embeds chapter tags during generation.
  - `src/core/chapter_reconvert.py:205` embeds chapter tags during reconversion.
  - `src/api/routes.py:642` updates title/author metadata only.
  - `src/api/routes.py:658` returns immediately after the JSON update.
  - `src/api/routes.py:718` updates `cover_url` only after cover upload.
  - `src/api/routes.py:720` returns without rewriting existing MP3 tags.
- Suggested improvement
  Extract a small retag helper that walks the chapter list in `metadata.json` and re-applies `embed_mp3_metadata()` to each existing MP3 after title, author, or cover changes.

  This keeps the app's JSON metadata, cover file, and embedded ID3 data aligned.

### Minor: Bookmark input is not validated, and the player trusts stored values blindly

- Issue description
  The bookmark endpoint accepts any `chapter` and `position` values, including negative positions and chapter numbers that do not exist. Those values are persisted and then fed straight back into the player, which can resume onto an invalid chapter or seek to an invalid offset.
- Evidence
  - `src/api/routes.py:600` defines the bookmark endpoint.
  - `src/api/routes.py:608` passes raw `chapter` and `position` directly into persistence.
  - `src/core/library.py:188` persists bookmarks with no validation.
  - `static/js/views/player.js:587` assigns `playerState.currentChapter = bookmark.chapter || 1`.
  - `static/js/views/player.js:594` sets `playerState.audioElement.currentTime = bookmark.position`.
- Suggested improvement
  Validate `chapter >= 1`, `position >= 0`, and, when book metadata exists, reject bookmarks beyond the known chapter count. On the client side, clamp any loaded bookmark to the available chapter list and to a non-negative playback offset.

### Minor: Dashboard refresh re-registers DOM listeners every time `initDashboardView()` is called

- Issue description
  The dashboard is refreshed after import and delete operations by calling `initDashboardView()` again on the same DOM tree. Each call adds another `input` listener to the search box and another `change` listener to the import file input, which causes duplicated handlers over time.
- Evidence
  - `static/js/views/dashboard.js:135` adds a search `input` listener.
  - `static/js/views/dashboard.js:142` adds an import `change` listener.
  - `static/js/views/dashboard.js:287` calls `await initDashboardView();` after import.
  - `static/js/views/dashboard.js:368` calls `await initDashboardView();` after delete.
- Suggested improvement
  Either bind listeners once, or replace `addEventListener` with idempotent assignment (`oninput`, `onchange`) in `initDashboardView()`.

### Minor: `saveCurrentBookmark()` depends on the implicit global `event` object

- Issue description
  `saveCurrentBookmark()` reads `event.target` without accepting `event` as a parameter. This works only in environments that expose a global event for inline handlers; it is brittle across browsers and breaks if the function is ever called programmatically.
- Evidence
  - `static/js/views/player.js:611` defines `async function saveCurrentBookmark()`.
  - `static/js/views/player.js:614` uses `const btn = event.target.closest("button");`.
- Suggested improvement
  Pass the event explicitly from the inline handler or pass the button element itself.

  Example:

  ```html
  <button onclick="saveCurrentBookmark(event)">...
  ```

  ```javascript
  async function saveCurrentBookmark(event) {
    const btn = event.currentTarget;
    ...
  }
  ```

## Logic & Edge Cases

- The portability import/export path is notably careful. `src/core/portability.py` validates archive member counts, total uncompressed size, duplicate entries, and path safety before writing files. That is one of the stronger subsystems in the repository.
- The bookmark flow is the main place where input validation and UI assumptions diverge. The server stores raw values, and the player assumes the payload is safe. That is a classic cross-layer correctness gap.
- The reconvert flow correctly uses a temporary file plus `os.replace()` retry logic, which is the right Windows-oriented approach. The main remaining edge case is metadata drift after title/author/cover edits, not the replacement logic itself.
- The progress and dashboard UIs generally match backend behavior, but the dashboard refresh path is stateful enough that repeated initialization should be treated as a real lifecycle case rather than a one-shot render.

## Simplification & Minimalism

- The code now has two concepts of "write tags": one in generation and one in reconversion. The next cleanup step should be a single helper that accepts book metadata plus chapter metadata and tags a file. That would also make post-edit retagging straightforward.
- `src/api/routes.py` has several routes that partially duplicate book loading and chapter existence checks. The existing helper functions are good; continuing to centralize those patterns will reduce drift.
- `static/js/views/player.js` mixes DOM rendering, playback state, editing workflow, reconversion polling, and metadata editing in one large file. The current code still works, but the next refactor boundary is clear: chapter text editing/reconversion and metadata editing can be lifted into small modules without changing user-visible behavior.

## Elegance & Idiomatic Enhancements

- `TTSEngine` would benefit from an explicit initialization policy instead of open-coded lazy checks across methods. A locked `_ensure_pipeline(lang_code)` pattern would make the concurrency story much easier to reason about.
- The frontend already uses a small `api` wrapper in `static/js/app.js`. Extending that pattern to cover direct `fetch()` calls still present in the player view would make error handling more uniform.
- For dashboard event binding, idempotent property handlers or delegated listeners would better fit the current re-init model than repeated ad hoc `addEventListener()` calls.

## Documentation & Testability Recommendations

- Add a security regression test for markdown cover extraction that uses a markdown file referencing a parent-directory image and asserts that extraction is rejected.
- Add a concurrency-focused unit or integration test around `TTSEngine` initialization, or at minimum isolate the model/pipeline creation path so it can be tested with a fake `KPipeline` and a synchronization assertion.
- Add tests that cover bookmark validation failures: negative position, chapter `0`, and chapter number larger than `total_chapters`.
- Add one API-level test proving that metadata edits and cover uploads retag existing MP3 chapters, once that behavior is implemented.
- The documentation refresh is in good shape overall, but once bookmark validation or retag-after-edit is added, `docs/API-Reference.md` should be updated to state those guarantees explicitly.

## Positive Observations

- The non-slow test suite is healthy and broad: 181 passing tests is strong evidence that core behavior is exercised regularly.
- `src/core/portability.py` shows unusually good defensive design for a local-file ZIP import/export feature: path normalization, duplicate detection, size limits, schema validation, and staged writes are all present.
- The chapter reconversion workflow in `src/core/chapter_reconvert.py` is thoughtfully implemented for Windows file-lock realities, especially the temp-file replacement and retry behavior.
- The recent MP3 metadata embedding work is well targeted and covered by focused tests; the remaining gap is consistency after later edits, not the tagging logic itself.

## Final Note

This codebase is already above the baseline for a small file-based local app: the backend is structured, the tests are meaningful, and the portability feature was built with real defensive thinking. The next quality step is not a rewrite. It is tightening the few remaining trust boundaries and lifecycle assumptions so the code behaves as predictably under hostile or concurrent inputs as it does in the happy path.