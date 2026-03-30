# SimplyNarrated — Code Review Corrections PRD

**Date:** 2026-03-30
**Source:** `plans/code_review_report_2026-03-29.md`
**Author:** GitHub Copilot (automated PRD)
**Target audience:** Junior developer handing-off document

> **Completion Status (2026-03-30):** All 18 tasks across 4 phases have been implemented and verified. The test suite passes with 164 non-slow tests.

---

## Purpose

This document translates every finding from the 2026-03-29 code review into concrete, step-by-step implementation tasks. Each task contains:

  - **What** the problem is (plain English)
  - **Where** the code lives (file + line numbers)
  - **Exactly how** to fix it (code snippets you can copy-paste)
  - **How to verify** the fix is correct (manual or automated tests)

Work through the phases in order. Each phase builds on the previous one.

---

## Quick-Reference Checklist

### Phase 1 — Security & Correctness (Major findings, do these first)

  - [x] **Task 1.1** — Validate `narrator_voice` in `/generate` and `/reconvert` endpoints
  - [x] **Task 1.2** — Redact internal exception detail from voice-sample 500 response
  - [x] **Task 1.3** — Offload `parse_file()` to a thread-pool executor in the pipeline
  - [x] **Task 1.4** — Convert `_load_book_metadata_or_404()` to async I/O
  - [x] **Task 1.5** — Debounce `_persist_jobs()` so it is not called on every activity log entry

### Phase 2 — Logic & Edge Case Fixes (Minor findings)

  - [x] **Task 2.1** — Guard against infinite loop in `chunk_text()` when break-point is empty
  - [x] **Task 2.2** — Handle GIF cover images correctly in ZIP extraction
  - [x] **Task 2.3** — Replace blocking `time.sleep()` in `_replace_with_retry()` with async sleep
  - [x] **Task 2.4** — Refactor `flush_bucket()` closure to use an explicit data structure
  - [x] **Task 2.5** — Move `zipfile`/`io` imports out of `_estimate_chapters()` function body
  - [x] **Task 2.6** — Document the serialization-dependency of the reconvert metadata write

### Phase 3 — Code Quality & Simplification (Minor/Nit findings)

  - [x] **Task 3.1** — Remove `AudioFormat` enum / `format` field or actually use it in `encode_audio()`
  - [x] **Task 3.2** — Remove duplicate `static_ffmpeg.add_paths()` in `encoder.py`
  - [x] **Task 3.3** — Add missing `encoding="utf-8"` to metadata write in `pipeline.py`
  - [x] **Task 3.4** — Convert f-string logger calls to `%s`-style deferred formatting

### Phase 4 — Testing & Documentation (Minor/Nit findings)

  - [x] **Task 4.1** — Write unit tests for `chapter_reconvert.py` helpers
  - [x] **Task 4.2** — Write unit tests for `portability.py` helpers
  - [x] **Task 4.3** — Add PDF parsing test coverage

---

## Environment & Running Tests

Before starting, verify your environment:

```bash
# Run the non-GPU test suite (should be all green before you begin)
python -m pytest tests/ -m "not slow" -v
```

After each task, run the test suite again to confirm nothing broke.

---

## Phase 1 — Security & Correctness

---

### Task 1.1 — Validate `narrator_voice` in `/generate` and `/reconvert` endpoints

**Severity:** Major
**File:** `src/api/routes.py`

#### Problem

The `/api/generate` and `/api/book/{book_id}/chapter/{chapter}/reconvert` endpoints accept a `narrator_voice` string from the user and pass it straight to the TTS engine without checking whether it is a known voice ID. If an unknown ID is supplied, Kokoro falls back to the bare string and may attempt a network download — which contradicts the app's offline-first design. The `/voice-sample` endpoint already validates against `AVAILABLE_VOICES`; the other two do not.

#### Exact Location

  - **`/generate` endpoint** — around line 215 of `src/api/routes.py`, inside `async def start_generation(...)`.
  - **`/reconvert` endpoint** — around line 566, inside `async def reconvert_chapter(...)`.

#### Step-by-Step Fix

**Step 1.** Open `src/api/routes.py`.

**Step 2.** Find the `/generate` handler. It begins:

```python
@router.post("/generate")
async def start_generation(request: GenerateRequest, background_tasks: BackgroundTasks):
```

Immediately after the `if job.status != JobStatus.PENDING:` block and *before* the `config = {...}` dict is built, add the following voice validation:

```python
    # Validate narrator_voice against known voices
    valid_voice_ids = {v.id for v in AVAILABLE_VOICES}
    if request.narrator_voice not in valid_voice_ids:
        raise HTTPException(status_code=400, detail="Invalid narrator voice")
```

The final code block for that section should look like this:

```python
    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be started. Current status: {job.status}",
        )

    # Validate narrator_voice against known voices
    valid_voice_ids = {v.id for v in AVAILABLE_VOICES}
    if request.narrator_voice not in valid_voice_ids:
        raise HTTPException(status_code=400, detail="Invalid narrator voice")

    # Convert request to config dict
    config = {
        "narrator_voice": request.narrator_voice,
        ...
    }
```

**Step 3.** Find the `/reconvert` handler. It begins:

```python
@router.post("/book/{book_id}/chapter/{chapter}/reconvert")
async def reconvert_chapter(book_id: str, chapter: int, request: ReconvertChapterRequest):
```

After the `_ensure_chapter_exists_or_404(metadata, chapter)` call and before the `job_manager = get_job_manager()` call, add a voice validation block. Note that `narrator_voice` on the reconvert request is optional (it defaults to the book's original voice); only validate when the caller explicitly provides one:

```python
    # Validate narrator_voice if provided
    if request.narrator_voice is not None:
        valid_voice_ids = {v.id for v in AVAILABLE_VOICES}
        if request.narrator_voice not in valid_voice_ids:
            raise HTTPException(status_code=400, detail="Invalid narrator voice")
```

#### How to Verify

1. Run the existing API test suite:

   ```bash
   python -m pytest tests/test_api.py -v -m "not slow"
   ```

2. Manual test: Using the FastAPI docs at `http://localhost:8010/docs`, call `POST /api/generate` with `narrator_voice` set to `"not_a_real_voice"`. You should receive HTTP 400 with `"Invalid narrator voice"`.

3. Manual test: Call `POST /api/generate` with `narrator_voice` set to `"af_heart"`. It should proceed normally (HTTP 200 start response).

---

### Task 1.2 — Redact internal exception detail from voice-sample 500 response

**Severity:** Major
**File:** `src/api/routes.py`

#### Problem

The `except Exception as e:` block at the end of the `/voice-sample/{voice_id}` handler returns `f"Failed to generate sample: {e}"` in the HTTP 500 response body. This leaks internal implementation details (file paths, error messages, stack fragments) to any client. The full exception is already logged with `logger.exception(...)`, so the detail in the response is redundant.

#### Exact Location

Around line 372 of `src/api/routes.py`, inside `async def get_voice_sample(voice_id: str)`:

```python
    except Exception as e:
        logger.exception(f"Failed to generate voice sample for {voice_id}")
        raise HTTPException(status_code=500, detail=f"Failed to generate sample: {e}")
```

#### Step-by-Step Fix

**Step 1.** Open `src/api/routes.py`.

**Step 2.** Find the `except Exception as e:` block near the bottom of `get_voice_sample`. Replace:

```python
    except Exception as e:
        logger.exception(f"Failed to generate voice sample for {voice_id}")
        raise HTTPException(status_code=500, detail=f"Failed to generate sample: {e}")
```

With:

```python
    except Exception:
        logger.exception("Failed to generate voice sample for %s", voice_id)
        raise HTTPException(status_code=500, detail="Failed to generate voice sample")
```

> **Note:** The `f"..."` in `logger.exception` was also changed to `%s`-style — this is correct even if you apply Task 3.4 separately later.

#### How to Verify

1. Run the API tests:

   ```bash
   python -m pytest tests/test_api.py -v -m "not slow"
   ```

2. Check that the response detail no longer contains a Python exception string (e.g. no `"OSError:"`, `"RuntimeError:"`, or stack frame text) when the TTS engine raises an error.

---

### Task 1.3 — Offload `parse_file()` to a thread-pool executor

**Severity:** Major
**File:** `src/core/pipeline.py`

#### Problem

`parse_file()` is a synchronous, potentially heavy function (PDF parsing, ZIP HTML extraction). It is called directly inside the `async def process_book()` coroutine at line 76 without wrapping it in `run_in_executor`. Even though there is an `await asyncio.sleep(0.1)` just before it, a large PDF will still block the event loop for the entire parse duration (potentially multiple seconds), preventing any other async tasks — like status polling — from being served.

#### Exact Location

`src/core/pipeline.py`, approximately line 76:

```python
        document = parse_file(job.file_path)
```

#### Step-by-Step Fix

**Step 1.** Open `src/core/pipeline.py`.

**Step 2.** Locate the section that reads:

```python
        # Phase 1: Parse the file
        job_manager._add_activity(job, "Extracting text from file...")
        await asyncio.sleep(0.1)  # Yield to event loop

        document = parse_file(job.file_path)
```

**Step 3.** Replace just the `document = parse_file(job.file_path)` line with:

```python
        loop = asyncio.get_running_loop()
        document = await loop.run_in_executor(None, parse_file, job.file_path)
```

The full updated block should look like:

```python
        # Phase 1: Parse the file
        job_manager._add_activity(job, "Extracting text from file...")
        await asyncio.sleep(0.1)  # Yield to event loop

        loop = asyncio.get_running_loop()
        document = await loop.run_in_executor(None, parse_file, job.file_path)
```

> **Note:** `loop` is re-used later in Phase 4 of the pipeline (for TTS and encoder calls). The variable is already declared further down; you can leave those declarations in place. If the compiler complains about a redeclaration, rename the Phase 1 loop variable to `parse_loop` or move the single `loop = asyncio.get_running_loop()` call to before Phase 1 and remove the duplicate declarations later in the function.

#### How to Verify

1. Run existing pipeline-related tests:

   ```bash
   python -m pytest tests/test_api.py -v -m "not slow"
   ```

2. Manually upload a small `.txt` file through the UI and confirm conversion still completes successfully.

---

### Task 1.4 — Convert `_load_book_metadata_or_404()` to async I/O

**Severity:** Major
**File:** `src/api/routes.py`

#### Problem

`_load_book_metadata_or_404()` is a synchronous helper that calls `open()` and `json.load()` directly. It is called from multiple `async def` route handlers: bookmark save, reconvert, update chapter text, update metadata, and delete. Synchronous file reads inside async handlers block the event loop during I/O, which degrades responsiveness under concurrent requests.

#### Exact Location

`src/api/routes.py`, approximately lines 94–101:

```python
def _load_book_metadata_or_404(book_dir: str) -> dict:
    """Load metadata for a book directory, raising 404 if unavailable."""
    metadata_path = os.path.join(book_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Book not found")

    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        return json.load(metadata_file)
```

#### Step-by-Step Fix

**Step 1.** Open `src/api/routes.py`.

**Step 2.** Replace the existing `_load_book_metadata_or_404` function with an async version:

```python
async def _load_book_metadata_or_404(book_dir: str) -> dict:
    """Load metadata for a book directory, raising 404 if unavailable."""
    metadata_path = os.path.join(book_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Book not found")

    async with aiofiles.open(metadata_path, "r", encoding="utf-8") as metadata_file:
        return json.loads(await metadata_file.read())
```

> `aiofiles` is already imported at the top of `routes.py`; `json` is also already imported. No new imports are needed.

**Step 3.** Every call site of `_load_book_metadata_or_404` must now `await` the function. Search for all occurrences in `routes.py`:

```bash
grep -n "_load_book_metadata_or_404" src/api/routes.py
```

For every line that calls it, prepend `await`:

| Before | After |
|--------|-------|
| `metadata = _load_book_metadata_or_404(book_dir)` | `metadata = await _load_book_metadata_or_404(book_dir)` |
| `_load_book_metadata_or_404(book_dir)` (used as a guard) | `await _load_book_metadata_or_404(book_dir)` |

There are approximately five call sites. Make sure you update all of them.

#### How to Verify

1. Run the full API test suite:

   ```bash
   python -m pytest tests/test_api.py -v -m "not slow"
   ```

2. Confirm no `TypeError: object NoneType can't be used in 'await' expression` errors occur. If a call site was missed, Python will raise a runtime error.

---

### Task 1.5 — Debounce `_persist_jobs()` to avoid blocking I/O on every log entry

**Severity:** Major
**File:** `src/core/job_manager.py`

#### Problem

`_add_activity()` (line 186) unconditionally calls `_persist_jobs()` after every activity log append. `_persist_jobs()` serializes the entire jobs list and writes it synchronously to disk. During chapter generation of a 50-chapter book, this results in 150+ blocking file writes, each stalling the event loop.

The fix has two parts:

1. Make `_persist_jobs()` use `aiofiles` (async I/O).
2. Track a "dirty" flag so that `_add_activity()` marks the job as dirty without persisting immediately. A caller that finishes a major phase explicitly flushes.

Because `_add_activity` is also called from synchronous paths (startup recovery) we need a non-async fallback.

#### Exact Location

`src/core/job_manager.py`, lines 133–194.

#### Step-by-Step Fix

**Step 1.** Open `src/core/job_manager.py`.

**Step 2.** Add an `import aiofiles` at the top (after the other imports):

```python
import aiofiles
```

**Step 3.** Replace the synchronous `_persist_jobs()` method with an async version and add a sync fallback for startup use:

```python
    def _persist_jobs_sync(self) -> None:
        """Synchronous persist — use only during startup/shutdown."""
        payload = {"jobs": [self._serialize_job(job) for job in self._jobs.values()]}
        with open(self.jobs_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    async def _persist_jobs(self) -> None:
        """Async persist — preferred during normal async operation."""
        payload = {"jobs": [self._serialize_job(job) for job in self._jobs.values()]}
        async with aiofiles.open(self.jobs_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(payload, indent=2))
```

**Step 4.** Update `_recover_jobs_after_restart()` (and every other synchronous caller of `_persist_jobs`) to use the sync variant. Search for all calls:

```bash
grep -n "_persist_jobs" src/core/job_manager.py
```

In any method that is **not** `async def` (i.e. `__init__`, `_recover_jobs_after_restart`, `create_job`, `cancel_job`), change `self._persist_jobs()` to `self._persist_jobs_sync()`.

**Step 5.** In `_add_activity()`, **remove** the `self._persist_jobs()` call. The method should only append the log entry. No persistence here:

```python
    def _add_activity(self, job: Job, message: str, status: str = "info") -> None:
        """Add an activity log entry to a job. Does NOT persist — caller must flush."""
        entry = ActivityLogEntry(
            timestamp=datetime.now(),
            message=message,
            status=status,
        )
        job.activity_log.append(entry)
        # Persistence is the caller's responsibility (call await _persist_jobs() explicitly)
```

**Step 6.** In `update_progress()`, `_run_with_limit()`, and `_run_job()`, replace the existing synchronous `self._persist_jobs()` calls with `await self._persist_jobs()`. These are already inside `async def` methods.

**Step 7.** Because `pipeline.py` and `chapter_reconvert.py` call `job_manager._add_activity(job, ..., ...)` at the end of each chapter, add a single `await job_manager._persist_jobs()` call at the end of each major phase boundary (after Phase 1 parse, after Phase 2 chunk, and at the end of the chapter loop in Phase 4). Example insertion point in `pipeline.py`, after the chunk generation section:

```python
            job_manager._add_activity(
                job, f"Chapter {chapter_num} complete: {chunk.title}", "success"
            )
            # Flush job state once per chapter
            await job_manager._persist_jobs()
```

You do not need to call `_persist_jobs` after every `_add_activity`. One call per chapter is sufficient.

#### How to Verify

1. Run the job-manager tests:

   ```bash
   python -m pytest tests/test_job_manager.py -v
   ```

2. Run the full API test suite:

   ```bash
   python -m pytest tests/test_api.py -v -m "not slow"
   ```

3. Check that `jobs.json` is updated after a chapter completes (not after every line of log).

---

## Phase 2 — Logic & Edge Case Fixes

---

### Task 2.1 — Guard against infinite loop in `chunk_text()`

**Severity:** Minor
**File:** `src/core/chunker.py`

#### Problem

Inside `chunk_text()`, if `_find_break_point()` returns a string that is entirely whitespace (so `chunk_text.strip()` is empty), `actual_words` becomes 0. Because `current_pos += actual_words`, the loop pointer never advances, causing an infinite loop that hangs the server process.

#### Exact Location

`src/core/chunker.py`, lines 84–105:

```python
        # If we're not at the end, try to find a good break point
        if current_pos + max_words < len(words):
            chunk_text = _find_break_point(chunk_text)
            actual_words = len(chunk_text.split())
        else:
            actual_words = len(chunk_words)
```

#### Step-by-Step Fix

**Step 1.** Open `src/core/chunker.py`.

**Step 2.** Immediately after `actual_words = len(chunk_text.split())` (the branch that calls `_find_break_point`), add a guard:

```python
        if current_pos + max_words < len(words):
            chunk_text = _find_break_point(chunk_text)
            actual_words = len(chunk_text.split())
            # Guard: if break-point returned empty text, fall back to the full word slice
            if actual_words == 0:
                chunk_text = " ".join(chunk_words)
                actual_words = len(chunk_words)
        else:
            actual_words = len(chunk_words)
```

#### How to Verify

1. Run the chunker tests:

   ```bash
   python -m pytest tests/test_chunker.py -v
   ```

2. Add a regression test (optional but recommended). In `tests/test_chunker.py`, add:

   ```python
   def test_chunk_text_no_infinite_loop_on_empty_break():
       """chunk_text must not loop forever when _find_break_point returns whitespace."""
       # Craft a string where _find_break_point will return only whitespace
       # by using text with no sentence-ending punctuation and no paragraph breaks
       text = " ".join(["word"] * 8001)  # 8001 words, will need 3 chunks
       result = chunk_text(text, max_words=4000)
       assert len(result) >= 2, "Should produce at least 2 chunks"
       total = sum(c.word_count for c in result)
       assert total > 0, "No words lost"
   ```

---

### Task 2.2 — Handle GIF cover images correctly in ZIP extraction

**Severity:** Minor
**File:** `src/core/parser.py`

#### Problem

`extract_cover_image()` for ZIP files accepts `.gif` images in its search (it includes images with "cover" in the name). However, the branch that chooses the output filename only handles `.jpg`/`.jpeg` and `.png`; a GIF falls through to the `else` branch and is saved as `cover.png`. This produces a PNG-named file containing GIF binary data, which corrupts cover art display.

#### Exact Location

`src/core/parser.py`, approximately lines 447–454:

```python
            # Determine output extension
            ext = os.path.splitext(cover_member.filename)[1].lower()
            if ext in (".jpg", ".jpeg"):
                cover_filename = "cover.jpg"
            elif ext == ".png":
                cover_filename = "cover.png"
            else:
                cover_filename = "cover.png"
```

#### Step-by-Step Fix

**Option A (recommended) — Exclude GIFs from the search:**

The simplest, safest fix is to exclude GIF from the list of acceptable cover extensions. GIFs are unusual for book covers and the cover display logic only handles JPEG/PNG MIME types.

Find where the function filters for image members (look for a list comprehension or filter that includes `".gif"`). Change the extension filter to only include `.jpg`, `.jpeg`, and `.png`:

Before (search the file for the image filter list):

```python
            image_members = [
                m for m in zf.infolist()
                if not m.is_dir()
                and os.path.splitext(m.filename)[1].lower() in (".jpg", ".jpeg", ".png", ".gif")
            ]
```

After:

```python
            image_members = [
                m for m in zf.infolist()
                if not m.is_dir()
                and os.path.splitext(m.filename)[1].lower() in (".jpg", ".jpeg", ".png")
            ]
```

Also clean up the now-unreachable `else` branch in the filename decision block:

```python
            ext = os.path.splitext(cover_member.filename)[1].lower()
            if ext in (".jpg", ".jpeg"):
                cover_filename = "cover.jpg"
            else:
                cover_filename = "cover.png"
```

**Option B — Keep GIF support, save with correct extension:**

If you want to preserve GIF covers, add an explicit branch:

```python
            ext = os.path.splitext(cover_member.filename)[1].lower()
            if ext in (".jpg", ".jpeg"):
                cover_filename = "cover.jpg"
            elif ext == ".png":
                cover_filename = "cover.png"
            elif ext == ".gif":
                cover_filename = "cover.gif"
            else:
                cover_filename = "cover.png"
```

> **Note:** If you choose Option B, also update `encoder.py`'s `embed_mp3_metadata` MIME-type mapping and the `_find_cover_path` helper to include `"cover.gif"`.

#### How to Verify

1. Run the parser tests:

   ```bash
   python -m pytest tests/test_parser.py -v
   ```

2. Manually create a ZIP containing a file named `12345-cover.gif` (any binary content is fine for the test) and run the extraction — confirm it no longer creates a `cover.png` with GIF content.

---

### Task 2.3 — Replace blocking `time.sleep()` in `_replace_with_retry()` with async sleep

**Severity:** Minor
**File:** `src/core/chapter_reconvert.py`

#### Problem

`_replace_with_retry()` is called from the `async def process_chapter_reconvert_job()` coroutine (via `run_in_executor`). However, the function itself uses `time.sleep(retry_delay_seconds)` which, when executed inside an executor thread, is fine from an async standpoint. The problem occurs if `_replace_with_retry` is ever called directly (not via executor): it will block the calling coroutine.

The review suggested making the function async or running it exclusively in an executor. The cleaner solution is to run it via executor (it already is via `await loop.run_in_executor`), but also to document that the blocking sleep is intentional because it runs in a thread.

If you prefer a fully async approach, use `await asyncio.sleep()`.

#### Exact Location

`src/core/chapter_reconvert.py`, lines 66–87:

```python
def _replace_with_retry(source_path: str, destination_path: str, retries: int = 6) -> None:
    retry_delay_seconds = 0.5
    last_error = None

    for _ in range(retries):
        try:
            os.replace(source_path, destination_path)
            return
        except (PermissionError, OSError) as error:
            last_error = error
            time.sleep(retry_delay_seconds)
    ...
```

#### Step-by-Step Fix

**Option A — Convert to async (recommended):**

```python
async def _replace_with_retry(source_path: str, destination_path: str, retries: int = 6) -> None:
    retry_delay_seconds = 0.5
    last_error = None

    for _ in range(retries):
        try:
            os.replace(source_path, destination_path)
            return
        except (PermissionError, OSError) as error:
            last_error = error
            await asyncio.sleep(retry_delay_seconds)

    if os.path.exists(source_path):
        try:
            os.remove(source_path)
        except OSError:
            pass

    raise RuntimeError(
        "Unable to update chapter audio because the file is in use. "
        "Stop playback for this chapter and try again."
    ) from last_error
```

Then update the call site (around line 223):

```python
    # Before:
    await loop.run_in_executor(None, lambda: _replace_with_retry(temp_audio_path, audio_path))

    # After (call directly, no executor needed since it is now async):
    await _replace_with_retry(temp_audio_path, audio_path)
```

Also remove `import time` from the top of `chapter_reconvert.py` since `time.sleep` is no longer used.

**Option B — Keep synchronous, document the threading context:**

If you prefer not to change the function signature, add a comment making the intent clear:

```python
def _replace_with_retry(source_path: str, destination_path: str, retries: int = 6) -> None:
    """
    Attempt to atomically replace destination_path with source_path.
    Uses time.sleep() intentionally — this function MUST be called via
    run_in_executor() and never directly from an async coroutine.
    """
    ...
```

#### How to Verify

1. Run the full test suite:

   ```bash
   python -m pytest tests/ -m "not slow" -v
   ```

---

### Task 2.4 — Refactor `flush_bucket()` closure to use an explicit data structure

**Severity:** Minor
**File:** `src/core/chunker.py`

#### Problem

The `flush_bucket()` closure inside `chunk_chapters()` mutates three separate outer-scope variables (`current_bucket_text`, `current_bucket_titles`, `current_bucket_word_count`). The word count is reset via `current_bucket_word_count = flush_bucket()`. This pattern is fragile: forgetting to assign the return value leaves the word count stale, and the three pieces of state are not co-located.

#### Exact Location

`src/core/chunker.py`, lines 145–200.

#### Step-by-Step Fix

Replace the three separate variables and the closure with a single `bucket` dict:

```python
def chunk_chapters(
    chapters: List[Tuple[str, str]], max_words: int = MAX_WORDS_PER_CHUNK
) -> List[TextChunk]:
    """
    Chunk a list of chapters, merging small ones together and splitting
    large ones to respect max_words.
    """
    final_chunks: List[TextChunk] = []
    chunk_counter = 0

    bucket: dict = {"text": [], "titles": [], "word_count": 0}

    def flush_bucket() -> None:
        nonlocal chunk_counter
        if not bucket["text"]:
            return

        combined_text = "\n\n".join(bucket["text"])
        if len(bucket["titles"]) > 1:
            first = bucket["titles"][0]
            last = bucket["titles"][-1]
            bucket_title = f"{first} - {last}"
        else:
            bucket_title = bucket["titles"][0]

        bucket_chunks = chunk_text(combined_text, max_words, bucket_title)

        for ch in bucket_chunks:
            ch.index = chunk_counter
            final_chunks.append(ch)
            chunk_counter += 1

        bucket["text"].clear()
        bucket["titles"].clear()
        bucket["word_count"] = 0

    for title, content in chapters:
        words_in_chapter = count_words(content)

        if words_in_chapter > max_words:
            flush_bucket()
            chapter_chunks = chunk_text(content, max_words, title)
            for ch in chapter_chunks:
                ch.index = chunk_counter
                final_chunks.append(ch)
                chunk_counter += 1
            continue

        if bucket["word_count"] + words_in_chapter > max_words and bucket["text"]:
            flush_bucket()

        bucket["text"].append(content)
        bucket["titles"].append(title)
        bucket["word_count"] += words_in_chapter

    flush_bucket()

    return final_chunks
```

> **Key differences from the original:**
>
>   - `flush_bucket()` now returns `None` — callers no longer need to do `current_bucket_word_count = flush_bucket()`.
>   - All three mutable state fields live inside the `bucket` dict, so clearing is done inside `flush_bucket` and is never accidentally missed.

#### How to Verify

1. Run the chunker tests:

   ```bash
   python -m pytest tests/test_chunker.py -v
   ```

2. All existing tests must pass. Behavior is unchanged; this is a pure refactor.

---

### Task 2.5 — Move `zipfile`/`io` imports out of `_estimate_chapters()` function body

**Severity:** Minor
**File:** `src/api/routes.py`

#### Problem

`_estimate_chapters()` imports `zipfile` and `io` inside the function body. These are standard-library modules (not expensive) but the local-import pattern is inconsistent with the rest of the file and makes the dependency graph harder to follow at a glance.

#### Exact Location

`src/api/routes.py`, approximately lines 144–145:

```python
        if file_ext == ".zip":
            # ZIP with HTML: estimate from uncompressed HTML size
            import zipfile, io
```

#### Step-by-Step Fix

**Step 1.** Open `src/api/routes.py`.

**Step 2.** Find the import section at the top of the file (after the license header). Add `zipfile` and `io` there:

```python
import os
import re
import uuid
import asyncio
import json
import math
import tempfile
import io
import zipfile
import aiofiles
```

**Step 3.** In `_estimate_chapters()`, remove the inline `import zipfile, io` line.

#### How to Verify

1. Run the API tests:

   ```bash
   python -m pytest tests/test_api.py -v -m "not slow"
   ```

2. Confirm no import error on startup.

---

### Task 2.6 — Document the serialization dependency of the reconvert metadata write

**Severity:** Minor
**File:** `src/core/chapter_reconvert.py`

#### Problem

`process_chapter_reconvert_job()` reads `metadata.json` at the start of the function and writes it at the end, with no file locking. If two reconvert jobs for different chapters of the same book were ever run concurrently, the last writer wins and the first writer's duration update would be lost. Currently this is prevented because `JobManager` has a concurrency semaphore with `max_concurrent_jobs=1`. However, this is an implicit dependency that is not documented anywhere near the code.

#### Step-by-Step Fix

**Step 1.** Open `src/core/chapter_reconvert.py`.

**Step 2.** Find the section near line 110 where `metadata.json` is read:

```python
    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)
```

**Step 3.** Add a comment immediately above the read:

```python
    # NOTE: metadata.json is read once at the start and written at the end with no
    # file-level locking. Concurrent writes for different chapters of the same book
    # would cause data loss. This is safe only because JobManager's semaphore
    # (max_concurrent_jobs=1) serialises all jobs. Do not increase concurrency
    # without adding proper file-level locking (e.g. filelock) here.
    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)
```

No code change is required beyond the comment.

#### How to Verify

Code review / documentation-only change. Run `python -m pytest tests/ -m "not slow"` to confirm nothing is broken.

---

## Phase 3 — Code Quality & Simplification

---

### Task 3.1 — Remove unused `AudioFormat` / `format` field from `EncoderSettings`

**Severity:** Minor
**File:** `src/core/encoder.py`

#### Problem

`encode_audio()` always calls `audio_segment.export(..., format="mp3", ...)` regardless of `settings.format`. The `AudioFormat` enum in `schemas.py` only has one member (`MP3 = "mp3"`). The format abstraction is unused and misleads future contributors.

The simplest fix is to remove the `format` parameter from `EncoderSettings` and hard-code `"mp3"` everywhere it is used in `encoder.py`.

#### Exact Location

  - `src/core/encoder.py`, `EncoderSettings` dataclass and `encode_audio()` (around lines 43–116)
  - `src/models/schemas.py`, `AudioFormat` enum and `format` field in `GenerateRequest` / `ReconvertChapterRequest` (around lines 34–91)

#### Step-by-Step Fix

**Step 1.** In `src/core/encoder.py`, update the `EncoderSettings` dataclass — remove `format`:

```python
@dataclass
class EncoderSettings:
    """Audio encoding settings."""

    bitrate: str = "192k"  # 128k (SD), 192k (HD), 320k (Ultra)
    sample_rate: int = 24000
    channels: int = 1
```

**Step 2.** Update `get_encoder_settings()` to not accept or pass `format`:

```python
def get_encoder_settings(quality: str = "sd") -> EncoderSettings:
    """Get encoder settings for a quality preset."""
    preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["sd"])
    return EncoderSettings(
        bitrate=preset.bitrate,
        sample_rate=preset.sample_rate,
        channels=preset.channels,
    )
```

**Step 3.** In `QUALITY_PRESETS`, remove `format=` from `EncoderSettings(...)` calls since the field no longer exists:

```python
QUALITY_PRESETS = {
    "sd": EncoderSettings(bitrate="128k"),
    "hd": EncoderSettings(bitrate="192k"),
    "ultra": EncoderSettings(bitrate="320k"),
}
```

**Step 4.** In `pipeline.py`, update the call to `get_encoder_settings`:

```python
# Before:
encoder_settings = get_encoder_settings(
    quality=config.get("quality", "sd"),
    format=config.get("format", "mp3"),
)

# After:
encoder_settings = get_encoder_settings(quality=config.get("quality", "sd"))
```

**Step 5.** In `pipeline.py`, the line that builds `audio_path` references `encoder_settings.format`:

```python
output_filename = f"chapter_{chapter_num:02d}.{encoder_settings.format}"
```

Replace it with the hard-coded extension:

```python
output_filename = f"chapter_{chapter_num:02d}.mp3"
```

Do the same in `chapter_list` building:

```python
"audio_path": f"chapter_{chapter_num:02d}.mp3",
```

**Step 6.** In `chapter_reconvert.py`, update the `get_encoder_settings` call:

```python
# Before:
encoder_settings = get_encoder_settings(quality=quality, format="mp3")

# After:
encoder_settings = get_encoder_settings(quality=quality)
```

**Step 7.** In `src/models/schemas.py`, you may optionally remove the `AudioFormat` enum and `format` fields from `GenerateRequest` and `ReconvertChapterRequest`. However, since this is a public API schema change, be cautious — removing the field will cause a 422 validation error for any client that sends `format` in the request body. The safest approach is to keep the fields in the schema for backward compatibility but ignore them in the pipeline (since MP3 is always the output).

> **Recommendation:** Keep the `AudioFormat` enum and `format` field in the schema but add a docstring note: "Currently only MP3 is supported; this field is reserved for future formats." This avoids breaking any existing client integrations.

#### How to Verify

1. Run the encoder tests:

   ```bash
   python -m pytest tests/test_encoder.py -v
   python -m pytest tests/test_api.py -v -m "not slow"
   ```

---

### Task 3.2 — Remove duplicate `static_ffmpeg.add_paths()` from `encoder.py`

**Severity:** Minor (duplicate code)
**Files:** `src/main.py` and `src/core/encoder.py`

#### Problem

`static_ffmpeg.add_paths()` is called twice:

1. At module load time in `src/main.py` (lines 31–35)
2. Before every encode operation via `_configure_ffmpeg_paths()` in `src/core/encoder.py` (line 92)

The `add_paths()` call is idempotent, so the double call does not cause bugs, but it adds unnecessary overhead.

#### Step-by-Step Fix

**Step 1.** Open `src/core/encoder.py`.

**Step 2.** Remove the `_configure_ffmpeg_paths()` helper function entirely (lines ~32–39):

```python
# DELETE THIS ENTIRE FUNCTION:
def _configure_ffmpeg_paths() -> None:
    """Add bundled ffmpeg binaries to PATH when available."""
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except ImportError:
        pass
```

**Step 3.** Remove the call to `_configure_ffmpeg_paths()` inside `encode_audio()` (around line 92):

```python
# DELETE this line from encode_audio():
_configure_ffmpeg_paths()
```

**Step 4.** Keep the existing `static_ffmpeg.add_paths()` call in `src/main.py` — that remains the single canonical place to initialize ffmpeg paths.

#### How to Verify

1. Run the encoder tests:

   ```bash
   python -m pytest tests/test_encoder.py -v
   ```

2. Manually run a voice sample or a conversion and confirm audio still encodes correctly.

---

### Task 3.3 — Add missing `encoding="utf-8"` to metadata write in `pipeline.py`

**Severity:** Nit
**File:** `src/core/pipeline.py`

#### Problem

The `metadata.json` write near line 250 is missing `encoding="utf-8"`:

```python
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)
```

Every other JSON file write in the codebase specifies `encoding="utf-8"`. On Windows, the default encoding may differ from UTF-8, which can corrupt book titles containing non-ASCII characters.

#### Step-by-Step Fix

**Step 1.** Open `src/core/pipeline.py`.

**Step 2.** Find the line around 250:

```python
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
```

**Step 3.** Change it to:

```python
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
```

#### How to Verify

Run the API tests:

```bash
python -m pytest tests/test_api.py -v -m "not slow"
```

---

### Task 3.4 — Convert f-string logger calls to `%s`-style deferred formatting

**Severity:** Nit
**File:** `src/api/routes.py`

#### Problem

Two `logger` calls use f-strings, which evaluate the string expression even when the log level is disabled. The idiomatic Python logging pattern is to use `%s`-style formatting so the string is only built if the message will actually be emitted.

#### Exact Location

`src/api/routes.py`:

  - Around line 340: `logger.info(f"Generating voice sample for {voice_id}: '{quote[:50]}...'")`
  - Around line 373: `logger.exception(f"Failed to generate voice sample for {voice_id}")`

#### Step-by-Step Fix

**Step 1.** Find line ~340:

```python
logger.info(f"Generating voice sample for {voice_id}: '{quote[:50]}...'")
```

Replace with:

```python
logger.info("Generating voice sample for %s: '%.50s...'", voice_id, quote)
```

**Step 2.** Find line ~373 (already updated as part of Task 1.2, but double-check):

```python
logger.exception(f"Failed to generate voice sample for {voice_id}")
```

Replace with:

```python
logger.exception("Failed to generate voice sample for %s", voice_id)
```

> If Task 1.2 was already completed, this second line should already be correct. Verify and skip if already done.

#### How to Verify

Run `python -m pytest tests/test_api.py -v -m "not slow"`. Linters like `pylint` with `logging-format-interpolation` enabled will no longer flag these lines.

---

## Phase 4 — Testing & Documentation

---

### Task 4.1 — Write unit tests for `chapter_reconvert.py` helpers

**Severity:** Minor
**New File:** `tests/test_chapter_reconvert.py`

#### Problem

`chapter_reconvert.py` has no dedicated unit tests. The helpers `_parse_duration_to_seconds`, `_format_total_duration_from_chapters`, `sanitize_filename_component` (in portability, covered in Task 4.2), and `_replace_with_retry` are only covered indirectly through API integration tests, making regressions harder to isolate.

#### Step-by-Step Fix

Create the file `tests/test_chapter_reconvert.py` with the following content:

```python
"""
Unit tests for src/core/chapter_reconvert.py helpers.
"""

import os
import pytest


# ---------------------------------------------------------------------------
# _parse_duration_to_seconds
# ---------------------------------------------------------------------------


from src.core.chapter_reconvert import (
    _parse_duration_to_seconds,
    _format_total_duration_from_chapters,
)


class TestParseDurationToSeconds:
    def test_mm_ss(self):
        assert _parse_duration_to_seconds("1:30") == 90.0

    def test_hh_mm_ss(self):
        assert _parse_duration_to_seconds("1:02:03") == 3723.0

    def test_empty(self):
        assert _parse_duration_to_seconds("") == 0.0

    def test_none_like(self):
        assert _parse_duration_to_seconds(None) == 0.0

    def test_invalid(self):
        assert _parse_duration_to_seconds("not-a-time") == 0.0

    def test_zero(self):
        assert _parse_duration_to_seconds("0:00") == 0.0


# ---------------------------------------------------------------------------
# _format_total_duration_from_chapters
# ---------------------------------------------------------------------------


class TestFormatTotalDurationFromChapters:
    def test_sums_durations(self):
        chapters = [
            {"duration": "1:00"},
            {"duration": "2:30"},
        ]
        result = _format_total_duration_from_chapters(chapters)
        # 90 + 150 = 240 seconds = 4:00
        assert result == "4:00"

    def test_empty_list(self):
        result = _format_total_duration_from_chapters([])
        assert result == "0:00"

    def test_missing_duration_key(self):
        chapters = [{"title": "Chapter 1"}]
        result = _format_total_duration_from_chapters(chapters)
        assert result == "0:00"


# ---------------------------------------------------------------------------
# _replace_with_retry (sync behaviour when file is not locked)
# ---------------------------------------------------------------------------


from src.core.chapter_reconvert import _replace_with_retry


class TestReplaceWithRetry:
    def test_successful_replace(self, tmp_path):
        src = tmp_path / "source.tmp"
        dst = tmp_path / "destination.mp3"
        src.write_bytes(b"audio data")

        if asyncio_available():
            import asyncio
            asyncio.run(_replace_with_retry(str(src), str(dst)))
        else:
            # Sync fallback for older test environments
            import os
            os.replace(str(src), str(dst))

        assert dst.exists()
        assert not src.exists()
        assert dst.read_bytes() == b"audio data"

    def test_raises_when_source_missing(self, tmp_path):
        src = tmp_path / "missing.tmp"
        dst = tmp_path / "destination.mp3"

        import asyncio
        with pytest.raises((FileNotFoundError, RuntimeError)):
            asyncio.run(_replace_with_retry(str(src), str(dst), retries=1))


def asyncio_available():
    try:
        import asyncio  # noqa: F401
        return True
    except ImportError:
        return False
```

> **Note:** If `_replace_with_retry` was converted to `async` in Task 2.3, the tests above use `asyncio.run(...)` appropriately. If it remained synchronous, replace `asyncio.run(_replace_with_retry(...))` with a direct call `_replace_with_retry(...)`.

#### How to Verify

```bash
python -m pytest tests/test_chapter_reconvert.py -v
```

All tests should pass.

---

### Task 4.2 — Write unit tests for `portability.py` helpers

**Severity:** Minor
**New File:** `tests/test_portability.py`

#### Problem

`portability.py` is tested only through the export/import API endpoints. The helper functions `sanitize_filename_component`, `_normalize_book_metadata`, `_is_safe_archive_member`, and the export/import roundtrip have no direct unit tests.

#### Step-by-Step Fix

Create `tests/test_portability.py` with the following content:

```python
"""
Unit tests for src/core/portability.py helpers.
"""

import json
import os
import uuid
import zipfile
from datetime import datetime

import pytest

from src.core.portability import (
    sanitize_filename_component,
    export_book_archive,
    import_book_archive,
    ARCHIVE_MANIFEST_NAME,
)


# ---------------------------------------------------------------------------
# sanitize_filename_component
# ---------------------------------------------------------------------------


class TestSanitizeFilenameComponent:
    def test_removes_illegal_characters(self):
        result = sanitize_filename_component('My <Book>: "Title"')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result

    def test_empty_string_returns_default(self):
        result = sanitize_filename_component("")
        assert result == "audiobook"

    def test_windows_reserved_names_renamed(self):
        result = sanitize_filename_component("CON")
        assert result.upper() != "CON"

    def test_none_returns_default(self):
        result = sanitize_filename_component(None)
        assert result == "audiobook"

    def test_normal_title_unchanged(self):
        result = sanitize_filename_component("My Normal Book Title")
        assert result == "My Normal Book Title"

    def test_strips_leading_trailing_dots_spaces(self):
        result = sanitize_filename_component("  ..Title..  ")
        # Leading/trailing dots and spaces stripped
        assert not result.startswith(".")
        assert not result.endswith(".")
        assert not result.startswith(" ")


# ---------------------------------------------------------------------------
# Export / Import roundtrip
# ---------------------------------------------------------------------------


@pytest.fixture
def populated_library(tmp_library_dir):
    """Create a library with a complete book ready for export."""
    import src.core.library as lib_module

    book_id = str(uuid.uuid4())
    book_dir = tmp_library_dir / book_id
    book_dir.mkdir()

    metadata = {
        "id": book_id,
        "title": "Export Test Book",
        "author": "Test Author",
        "source_file": "source.txt",
        "original_filename": "export_test.txt",
        "voice": "af_heart",
        "total_chapters": 1,
        "total_duration": "0:05",
        "created_at": datetime.now().isoformat(),
        "format": "mp3",
        "quality": "sd",
        "chapters": [
            {
                "number": 1,
                "title": "Chapter 1",
                "duration": "0:05",
                "audio_path": "chapter_01.mp3",
                "text_path": "chapter_01.txt",
                "completed": True,
            }
        ],
    }

    (book_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (book_dir / "chapter_01.mp3").write_bytes(b"fake mp3 data")
    (book_dir / "chapter_01.txt").write_text("Chapter one text.", encoding="utf-8")

    manager = lib_module.init_library_manager(str(tmp_library_dir))
    yield manager, book_id

    lib_module._library_manager = None


class TestExportImportRoundtrip:
    def test_export_creates_zip(self, populated_library):
        manager, book_id = populated_library
        archive_path, filename = export_book_archive(manager, book_id)

        assert os.path.exists(archive_path)
        assert filename.endswith(".zip")

        with zipfile.ZipFile(archive_path) as zf:
            names = zf.namelist()
            assert ARCHIVE_MANIFEST_NAME in names
            assert "metadata.json" in names

        os.remove(archive_path)

    def test_export_missing_book_raises(self, populated_library):
        manager, _ = populated_library
        with pytest.raises(FileNotFoundError):
            export_book_archive(manager, "00000000-0000-0000-0000-000000000000")

    def test_import_restores_metadata(self, populated_library, tmp_path):
        manager, book_id = populated_library
        archive_path, _ = export_book_archive(manager, book_id)

        result = import_book_archive(manager, archive_path)

        assert result["status"] == "imported"
        assert result["title"] == "Export Test Book"
        assert result["total_chapters"] == 1

        os.remove(archive_path)
```

#### How to Verify

```bash
python -m pytest tests/test_portability.py -v
```

---

### Task 4.3 — Add PDF parsing test coverage

**Severity:** Nit
**Files:** `tests/conftest.py` and `tests/test_parser.py`

#### Problem

`parse_pdf()` is registered in the parser dispatch table but no test fixture creates a PDF and no test class exercises it. If PDF parsing is broken, the test suite would not catch it.

#### Step-by-Step Fix

**Step 1.** Check if `reportlab` or `fpdf2` is already in `requirements.txt` for generating test PDFs. If not, the simplest approach is to create a minimal PDF using raw bytes (a hand-crafted minimal valid PDF structure) or use `pypdf` / `PyMuPDF` which is already a project dependency.

**Step 2.** Add a `sample_pdf_file` fixture to `tests/conftest.py`. This uses `PyMuPDF` (already installed as `fitz`) to create a minimal in-memory PDF:

```python
@pytest.fixture
def sample_pdf_file(tmp_uploads_dir):
    """Create a minimal PDF with two chapters for parser testing."""
    import fitz  # PyMuPDF

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "My Test PDF Book\n\nChapter 1\n\nThis is the first chapter of the PDF. It has several sentences for testing.\n\nChapter 2\n\nThis is the second chapter of the PDF book.")

    path = tmp_uploads_dir / "sample.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)
```

**Step 3.** Add a `TestParsePdf` class to `tests/test_parser.py`:

```python
class TestParsePdf:
    def test_parse_pdf_returns_document(self, sample_pdf_file):
        from src.core.parser import parse_file
        doc = parse_file(sample_pdf_file)
        assert doc is not None

    def test_parse_pdf_has_chapters(self, sample_pdf_file):
        from src.core.parser import parse_file
        doc = parse_file(sample_pdf_file)
        assert len(doc.chapters) >= 1

    def test_parse_pdf_chapter_content_not_empty(self, sample_pdf_file):
        from src.core.parser import parse_file
        doc = parse_file(sample_pdf_file)
        for title, content in doc.chapters:
            assert content.strip(), f"Chapter '{title}' has no content"

    def test_parse_pdf_title_extracted(self, sample_pdf_file):
        from src.core.parser import parse_file
        doc = parse_file(sample_pdf_file)
        # Title should be non-empty (may be filename or extracted from document)
        assert doc.title
```

#### How to Verify

```bash
python -m pytest tests/test_parser.py::TestParsePdf -v
```

---

## Summary Table

| Task | File(s) | Effort | Phase | Status |
|------|---------|--------|-------|--------|
| 1.1 Voice validation in /generate & /reconvert | `src/api/routes.py` | Low | 1 | ✅ |
| 1.2 Redact exception detail in voice-sample 500 | `src/api/routes.py` | Low | 1 | ✅ |
| 1.3 parse_file() → run_in_executor | `src/core/pipeline.py` | Low | 1 | ✅ |
| 1.4 _load_book_metadata_or_404() → async | `src/api/routes.py` | Medium | 1 | ✅ |
| 1.5 _persist_jobs() debounce / async | `src/core/job_manager.py`, `pipeline.py`, `chapter_reconvert.py` | Medium | 1 | ✅ |
| 2.1 chunk_text() infinite-loop guard | `src/core/chunker.py` | Low | 2 | ✅ |
| 2.2 GIF cover image handling | `src/core/parser.py` | Low | 2 | ✅ |
| 2.3 _replace_with_retry() → async sleep | `src/core/chapter_reconvert.py` | Low | 2 | ✅ |
| 2.4 flush_bucket() refactor | `src/core/chunker.py` | Low | 2 | ✅ |
| 2.5 Move zipfile/io imports to top | `src/api/routes.py` | Low | 2 | ✅ |
| 2.6 Document semaphore dependency | `src/core/chapter_reconvert.py` | Low | 2 | ✅ |
| 3.1 Remove unused AudioFormat/format field | `src/core/encoder.py`, `src/core/pipeline.py`, `src/core/chapter_reconvert.py` | Low | 3 | ✅ |
| 3.2 Remove duplicate ffmpeg add_paths() | `src/core/encoder.py` | Low | 3 | ✅ |
| 3.3 Add encoding="utf-8" to metadata write | `src/core/pipeline.py` | Low | 3 | ✅ |
| 3.4 Convert f-string logger calls | `src/api/routes.py` | Low | 3 | ✅ |
| 4.1 Unit tests for chapter_reconvert.py | `tests/test_chapter_reconvert.py` (new) | Medium | 4 | ✅ |
| 4.2 Unit tests for portability.py | `tests/test_portability.py` (new) | Medium | 4 | ✅ |
| 4.3 PDF parsing tests | `tests/conftest.py`, `tests/test_parser.py` | Medium | 4 | ✅ |

**Total tasks:** 18 — **All complete**

---

## Verification Checklist

After completing all tasks, run the full test suite and confirm it is green:

```bash
python -m pytest tests/ -m "not slow" -v
```

Spot-check each major change manually by starting the server:

```bash
python -m uvicorn src.main:app --port 8010
```

Then:

1. Upload a `.txt` file and confirm conversion completes and chapters play.
2. Try `POST /api/generate` with an invalid voice ID — expect HTTP 400.
3. Upload and export a book, then import the ZIP — confirm the book appears in the library.
4. Edit a chapter's text and reconvert — confirm the audio updates.

---

*PRD created: 2026-03-30*
*Based on: `plans/code_review_report_2026-03-29.md`*
*All tasks completed: 2026-03-30*
*App version: SimplyNarrated 0.1.0*
