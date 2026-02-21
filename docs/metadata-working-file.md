# Metadata Editing — Working File

> **Purpose:** Trace the full metadata-save workflow, identify the performance
> bottleneck, and propose elegant alternatives that avoid copying the entire
> audiobook file.

---

## Table of Contents

1. [Current Workflow — End-to-End Trace](#1-current-workflow--end-to-end-trace)
2. [Why It Is Slow](#2-why-it-is-slow)
3. [Proposed Solutions](#3-proposed-solutions)
   - [Option A — Mutagen (in-place tag rewrite)](#option-a--mutagen-in-place-tag-rewrite)
   - [Option B — Hybrid Mutagen + ffmpeg (tags via Mutagen, cover art via ffmpeg)](#option-b--hybrid-mutagen--ffmpeg)
   - [Option C — ffmpeg `-movflags faststart` streaming rewrite](#option-c--ffmpeg--movflags-faststart-streaming-rewrite)
4. [Recommendation](#4-recommendation)
5. [Implementation Sketch](#5-implementation-sketch)
6. [Risk / Rollback](#6-risk--rollback)

---

## 1. Current Workflow — End-to-End Trace

### 1.1 Frontend: Opening the Edit Modal

| Step | Code Location | What Happens |
| ---- | ------------ | ------------ |
| **User clicks book cover** | `player.js` → `renderPlayerView()` line 37 | The cover `<div>` has `onclick="openEditMetaModal()"`. |
| **`openEditMetaModal()`** | `player.js` lines 739–763 | Pre-fills `#meta-title` and `#meta-author` from `playerState.book`. Resets the cover file input. Shows current cover in `#meta-cover-preview`. Removes the `hidden` class from `#meta-modal`. |
| **User edits fields** | HTML in `renderPlayerView()` lines 163–217 | Standard `<input>` fields for title, author, and a file picker for cover image (JPG/PNG, max 5 MB). |

### 1.2 Frontend: Saving (the "Save" button)

| Step | Code Location | What Happens |
| ---- | ------------ | ------------ |
| **`saveMetadata()`** | `player.js` lines 836–890 | Reads title, author, and cover file from the modal inputs. Builds an `updates` object containing only changed fields. If nothing changed, closes modal and returns early. |
| **`withReleasedPlayerHandle(work)`** | `player.js` lines 794–834 | **Critical step.** Before sending the API request, this function: (1) pauses playback, (2) removes the `src` attribute from the `<audio>` element and calls `audio.load()` to release the browser's file handle, (3) waits 120 ms. This is necessary because **on Windows, the streaming response holds an open file handle** that would prevent the backend from replacing the file. After the `work()` callback completes, it re-sets the audio `src` with a cache-busting query param, waits for `loadedmetadata`, restores `currentTime`, and resumes playback if it was previously playing. |
| **Cover upload** (if changed) | `app.js` → `api.uploadCover(bookId, file)` lines 191–204 | Sends a `POST /api/book/{bookId}/cover` with `FormData`. |
| **Text metadata update** (if changed) | `app.js` → `api.updateMetadata(bookId, data)` lines 167–178 | Sends a `PATCH /api/book/{bookId}` with JSON body `{ title, author }`. |
| **UI refresh** | `player.js` lines 875–883 | Updates `playerState.book.title`, `playerState.book.author`, and DOM elements `#book-title` / `#book-author`. |

### 1.3 Backend: `PATCH /api/book/{book_id}` → `update_book_metadata()`

**File:** `src/api/routes.py` lines 580–630

```txt
Step 1  →  Validate book_id (UUID format check, prevent path traversal)
Step 2  →  Parse UpdateMetadataRequest (Pydantic: optional title & author)
Step 3  →  Resolve book_dir, book object, and book_file_path via LibraryManager
Step 4  →  Merge: new_title = updates.title or existing title
            new_author = updates.author or existing author
Step 5  →  Set abort_event for this book_id to cancel any active audio stream
            (prevents the streaming response from holding the file handle open)
Step 6  →  await asyncio.sleep(0.2) — give streams time to close
Step 7  →  Call update_m4a_metadata(...)   ← THE BOTTLENECK
Step 8  →  Clear abort_event
Step 9  →  Return { status, book_id, title, author }
```

### 1.4 Backend: `POST /api/book/{book_id}/cover` → `upload_cover()`

**File:** `src/api/routes.py` lines 637–720

Follows a nearly identical pattern to `update_book_metadata()`:

```txt
Step 1–4  →  Validate, read cover bytes, write cover.jpg/cover.png to book_dir
Step 5    →  Set abort_event, sleep 0.2s
Step 6    →  Call update_m4a_metadata(...)  with cover_path  ← SAME BOTTLENECK
Step 7    →  Clear abort_event
Step 8    →  Return { status, cover_url }
```

### 1.5 Core: `update_m4a_metadata()` — The Bottleneck Function

**File:** `src/core/encoder.py` lines 583–671

This is where the expensive work happens. Here is the **exact sequence**:

```txt
1.  Check that file_path exists
2.  Define output_tmp = "{file_path}.tmp.metadata"
3.  Clean up any leftover .tmp.metadata file
4.  Create a temporary directory (tempfile.TemporaryDirectory)
5.  Write an FFMETADATA1-format text file into the temp dir via _write_ffmetadata()
    - Contains: title, album, artist, album_artist, comment (SNMETA JSON), chapters
6.  Build the ffmpeg command:
        ffmpeg -y
          -i {original_file}                  ← reads the ENTIRE input file
          -f ffmetadata -i {metadata.txt}      ← the new metadata
          [-i {cover_path} -map 2:v -c:v mjpeg -disposition:v:0 attached_pic]
          -map 0:a                             ← copy audio stream
          -map_metadata 1                      ← use metadata from input #1
          -map_chapters 1                      ← use chapters from input #1
          -c:a copy                            ← DO NOT re-encode audio
          -f mp4
          {output_tmp}                         ← writes to .tmp.metadata file
7.  Run ffmpeg  ← THIS IS THE SLOW PART
    Even with -c:a copy (no re-encoding), ffmpeg must:
      a) Read the entire input .m4a file
      b) Parse and demux every audio packet
      c) Write every audio packet to the new .tmp.metadata file
      d) Write the new moov atom with updated metadata
    For a 2 GB audiobook, this means reading 2 GB + writing 2 GB = 4 GB of I/O
8.  Delete the temp directory (automatic via context manager)
9.  Call _replace_with_retries(source=output_tmp, target=file_path)
    - os.replace() atomically replaces the original file
    - Retries up to `replace_retries` times (default 5, but routes pass 40)
    - On PermissionError, calls _force_close_file_handles_windows()
      which uses the Windows Restart Manager API (rstrtmgr.dll) to
      identify and forcefully close external file handles
10. If anything fails, clean up the .tmp.metadata file
```

### 1.6 Visual Summary (Data Flow Diagram)

```txt
┌────────────────────────────────────────────────────────────────────┐
│  BROWSER                                                           │
│                                                                    │
│  User clicks Save ──→ withReleasedPlayerHandle() ──→ release      │
│  audio.src            audio handle, wait 120ms                     │
│       │                                                            │
│       ├─► POST /api/book/{id}/cover  (if cover changed)           │
│       └─► PATCH /api/book/{id}       (if title/author changed)    │
└────────────────────────┬───────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────────┐
│  FASTAPI SERVER                                                    │
│                                                                    │
│  routes.py → update_book_metadata()                                │
│       │                                                            │
│       ├─ abort_event.set()  →  kills active streaming responses    │
│       ├─ await sleep(0.2s)                                         │
│       │                                                            │
│       └─ encoder.update_m4a_metadata()                             │
│              │                                                     │
│              ├─ _write_ffmetadata()   →  tiny text file (~1KB)     │
│              ├─ ffmpeg -c:a copy     →  READS + WRITES FULL FILE  │
│              │     Input:  original.m4a  (e.g. 2 GB)              │
│              │     Output: original.m4a.tmp.metadata (2 GB copy)  │
│              │     Time:   ~1-5 minutes for large files           │
│              │                                                     │
│              └─ os.replace(tmp → original)                         │
│                    └─ _force_close_file_handles_windows() on fail  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Why It Is Slow

The root cause is that **ffmpeg cannot modify MP4/M4A metadata in-place**.
The MP4 container format stores its structural metadata (the `moov` atom)
separately from the media data (the `mdat` atom). When ffmpeg writes a new
output file, it must:

1. **Read every byte** of the `mdat` (audio data) from the original file.
2. **Copy every byte** of the `mdat` to the new temporary file.
3. **Write a new `moov` atom** at the end (or beginning with `-movflags faststart`).

Even though `-c:a copy` avoids re-encoding, the **byte-for-byte I/O is still
O(filesize)**. For a 2 GB audiobook, this means approximately 4 GB of disk I/O
(2 GB read + 2 GB write), which takes **1–5+ minutes** depending on disk speed.

Additionally, on Windows:

- The browser's streaming audio response holds a file handle that must be released.
- The Windows kernel sometimes delays releasing file handles, requiring the
  Restart Manager API hack (`_force_close_file_handles_windows`).
- Multiple retry loops (`_replace_with_retries` with 40 retries × 0.25s)
  add up to potentially **10 additional seconds** of waiting.

### Cost Breakdown for a Typical 2 GB Audiobook

| Phase | Time |
| ----- | ------ |
| Frontend: release audio handle + wait | ~0.3s |
| Backend: abort stream + sleep | ~0.2s |
| Backend: write ffmetadata file | ~0.001s |
| **Backend: ffmpeg -c:a copy (2 GB in → 2 GB out)** | **60–300s** ★ |
| Backend: os.replace (atomic rename) | ~0.01s |
| Backend: retry loop on PermissionError | 0–10s |
| Frontend: reload audio src + seek | ~1s |
| **Total** | **~62–312s** |

The ffmpeg step dominates at **97%+** of total time.

---

## 3. Proposed Solutions

### Option A — Mutagen (in-place tag rewrite)

**Library:** [Mutagen](https://mutagen.readthedocs.io/) (`pip install mutagen`)

**How it works:**

Mutagen's `mutagen.mp4.MP4` class can read and write iTunes/MP4 metadata tags
directly inside the existing file. It understands the MP4 container structure
and modifies only the `moov` atom, **without touching the `mdat` (audio data)
at all**.

If the new metadata fits within the existing padding of the `moov` atom, the
write is truly in-place (just a few KB of I/O). If the metadata grows beyond
the padding, Mutagen shifts data internally — but even in the worst case, it's
dramatically faster than rewriting the entire file because it only moves the
structural metadata, not the audio.

**What Mutagen can do:**

- ✅ Read/write title (`\xa9nam`), artist (`\xa9ART`), album (`\xa9alb`), album_artist (`aART`)
- ✅ Read/write custom freeform tags (like our `SNMETA:` comment)
- ✅ Read/write cover art (`covr`) — embedded JPEG/PNG
- ✅ Read chapter information from `moov.udta.chpl`
- ⚠️ **Chapters:** Can read chapters from the Nero chapter format (`chpl`), but
  **cannot reliably write ffmpeg-style chapters** (which use a separate chapter
  track with `TIMEBASE` entries). This is the main limitation.

**Performance:**

- Modifying title/author/comment: **< 0.1 seconds** regardless of file size
- Adding/replacing cover art: **< 1 second** for most images
- Time complexity: **O(metadata_size)** not O(file_size)

**Tag Mapping:**

| SimplyNarrated Field | Current ffmetadata key | Mutagen MP4 key |
| --------------------- | ---------------------- | ----------------- |
| Title | `title` | `\xa9nam` |
| Album | `album` | `\xa9alb` |
| Artist | `artist` | `\xa9ART` |
| Album Artist | `album_artist` | `aART` |
| Comment (SNMETA JSON) | `comment` | `\xa9cmt` |
| Cover Art | embedded via ffmpeg | `covr` (as `MP4Cover`) |

**Limitation: Chapter Metadata**

Mutagen uses the **Nero chapter format** (`moov.udta.chpl`), which stores
chapters as `(start_time_100ns, title)` pairs. Our codebase currently uses
**ffmpeg's FFMETADATA1 chapter format**, which creates a proper chapter track
with `TIMEBASE`, `START`, `END`, and custom tags per chapter
(`simplynarrated_chapter`, `simplynarrated_transcript_start`,
`simplynarrated_transcript_end`).

These per-chapter custom tags are **not representable** in the Nero chapter
format. However, there's a workaround:

- **Embed the chapter-level custom data into the global SNMETA comment.** Since
  chapter structure rarely changes during a metadata edit (users typically only
  change title/author/cover), we can serialize the chapter-level metadata into
  the existing `SNMETA:` JSON blob in the comment field.

This is viable because **metadata edits never change chapter boundaries** — chapters
are only defined during initial audiobook generation.

### Option B — Hybrid Mutagen + ffmpeg

**Strategy:** Use Mutagen for the common case (title, author, comment), and only
fall back to the full ffmpeg rewrite when chapter metadata or cover art needs
to change in complex ways.

```txt
if only title/author changed:
    → Mutagen in-place  (~0.1s)
elif only cover changed:
    → Mutagen in-place with covr tag  (~0.5s)
elif chapters need to change:
    → ffmpeg full rewrite  (existing slow path, but this almost never happens)
```

**Advantages:**

- The most common operation (title/author edit) becomes near-instant.
- Cover art uploads also become fast (Mutagen embeds cover internally).
- No risk of breaking chapter metadata, since we only use the slow path when
  chapters actually change.
- Easy to implement — the slow path already exists and is well-tested.

**Disadvantages:**

- Mutagen becomes a new dependency.
- Two code paths for metadata writing means slightly more complexity.
- Need to handle the dual-storage of cover art (both `cover.jpg` on disk and
  embedded in the M4A via `covr` tag).

### Option C — ffmpeg `-movflags faststart` streaming rewrite

**Strategy:** Keep ffmpeg but optimize the command to minimize I/O.

This doesn't eliminate the full-file copy, but could potentially reduce it by:

1. Using `-movflags +faststart` to place the `moov` atom at the beginning.
2. Using an OS-level file hole or sparse copy if supported.

**Reality check:** This option **does not actually solve the problem**. Even with
`-movflags faststart`, ffmpeg still performs a full read + write of the file.
The `faststart` flag just performs an additional internal copy to move the `moov`
atom from the end to the beginning. It actually makes the process *slightly
slower* — not faster.

**Verdict:** ❌ Not viable. Included here for completeness.

---

## 4. Recommendation

**Option B (Hybrid Mutagen + ffmpeg)** is the recommended approach.

### Rationale

1. **Covers 99% of user interactions instantly.** Users almost exclusively edit
   title, author, and cover art. These operations drop from minutes to
   sub-second with Mutagen.

2. **Zero risk to audio data.** Mutagen never touches the `mdat` atom. The audio
   bitstream remains byte-for-byte identical.

3. **Preserves the battle-tested ffmpeg path for edge cases.** If we ever need
   to modify chapter boundaries or rebuild the file structure, the existing
   `update_m4a_metadata()` function remains available as a fallback.

4. **Mutagen is a mature, well-maintained library** (15+ years, actively
   developed, used by major projects like Picard, Quod Libet, and beets).

5. **Minimal new code.** The implementation requires roughly 50–80 lines of
   new Python code (the Mutagen wrapper), plus minor changes to the route
   handlers to choose the fast path.

6. **The chapter limitation is a non-issue in practice.** Users never change
   chapter boundaries in the metadata editor — those are set during audiobook
   generation and remain fixed. The SNMETA comment already carries all
   custom chapter-level data.

### What the User Experience Becomes

| Scenario | Before | After |
| -------- | ------ | ----- |
| Change title | 1–5 minutes | < 0.2 seconds |
| Change author | 1–5 minutes | < 0.2 seconds |
| Change title + author | 1–5 minutes | < 0.2 seconds |
| Upload new cover | 1–5 minutes | < 1 second |
| Change title + upload cover | 1–5 minutes | < 1 second |

---

## 5. Implementation Sketch

### 5.1 New dependency

```txt
# requirements.txt — add under "Audio Processing"
mutagen>=1.47.0
```

### 5.2 New function: `update_m4a_metadata_fast()`

```python
# src/core/encoder.py — new function

from mutagen.mp4 import MP4, MP4Cover

def update_m4a_metadata_fast(
    file_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    cover_path: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Update M4A metadata in-place using Mutagen.
    
    This modifies only the moov atom — audio data is never read or written.
    For a 2 GB file, this takes < 0.2s instead of 1-5 minutes.
    
    Limitations: Cannot modify chapter structure. Use update_m4a_metadata()
    (the ffmpeg path) if chapters need to change.
    """
    audio = MP4(file_path)

    if title is not None:
        audio.tags["\xa9nam"] = [title]
        audio.tags["\xa9alb"] = [title]

    if author is not None:
        audio.tags["\xa9ART"] = [author]
        audio.tags["aART"] = [author]

    # Preserve and update SNMETA custom payload in comment field
    if custom_metadata is not None:
        payload = {
            str(k): v for k, v in custom_metadata.items() if v is not None
        }
        audio.tags["\xa9cmt"] = ["SNMETA:" + json.dumps(payload, separators=(",", ":"))]

    # Embed cover art directly into the file
    if cover_path and os.path.exists(cover_path):
        with open(cover_path, "rb") as f:
            cover_data = f.read()

        ext = os.path.splitext(cover_path)[1].lower()
        image_format = (
            MP4Cover.FORMAT_JPEG if ext in (".jpg", ".jpeg")
            else MP4Cover.FORMAT_PNG
        )
        audio.tags["covr"] = [MP4Cover(cover_data, imageformat=image_format)]

    audio.save()
    return file_path
```

### 5.3 Updated route: choose fast path when possible

```python
# src/api/routes.py — update_book_metadata()

# Replace the call to update_m4a_metadata() with:
from src.core.encoder import update_m4a_metadata, update_m4a_metadata_fast

# In the try block:
update_m4a_metadata_fast(
    file_path=book_file_path,
    title=new_title,
    author=new_author,
    cover_path=find_cover_path(book_dir),
    custom_metadata={
        "SIMPLYNARRATED_ID": book.id,
        "SIMPLYNARRATED_CREATED_AT": book.created_at.isoformat(),
        "SIMPLYNARRATED_ORIGINAL_FILENAME": book.original_filename,
        "SIMPLYNARRATED_TRANSCRIPT_PATH": book.transcript_path,
    },
)
```

### 5.4 Updated `read_m4a_metadata()` — comment field compatibility

The current `read_m4a_metadata()` reads the comment from ffprobe's format tags.
The SNMETA payload will now be in the `\xa9cmt` MP4 tag. ffprobe already reads
this field and exposes it as the `comment` tag, so **no changes are needed** to
the reader — it will work transparently with both the old ffmpeg-written files
and the new Mutagen-written files.

### 5.5 Frontend simplification

With the fast path, the metadata save becomes so fast that we can simplify the
frontend flow:

- The `withReleasedPlayerHandle()` wrapper may still be needed for cover art
  changes (since the M4A file is still being modified), but the wait time
  drops from minutes to under a second.
- Consider removing the abort_event mechanism for the fast path (since the
  file modification is atomic from the OS perspective — Mutagen uses
  write-then-rename internally when padding is insufficient).

### 5.6 Test plan

| Test Case | Expected Result |
| --------- | --------------- |
| Update title only | Title changes in < 0.5s, audio plays correctly |
| Update author only | Author changes in < 0.5s, chapters preserved |
| Update title + author | Both change, SNMETA comment preserved |
| Upload cover only | Cover embedded in M4A, visible in player |
| Update title + cover | Both change simultaneously |
| Verify chapter preservation | All chapter timestamps and custom tags intact |
| Verify SNMETA round-trip | read_m4a_metadata() returns correct custom fields |
| Large file (2 GB+) | Operation completes in < 1s |
| Concurrent playback | Audio resumes correctly after edit |
| Windows file handle | No PermissionError during save |

---

## 6. Risk / Rollback

### Risks

| Risk | Likelihood | Mitigation |
| ---- | --------- | ---------- |
| Mutagen corrupts file | Very Low | Mutagen is battle-tested (15+ years). Keep ffmpeg path as fallback. Backup file before first save if paranoid. |
| Comment field format mismatch | Low | ffprobe reads `\xa9cmt` as `comment` — verified compatible. |
| Chapters lost during save | None | Mutagen does not touch chapter atoms when saving tag-only changes. |
| Padding exhausted on repeated edits | Very Low | Mutagen handles padding automatically. Worst case: internal file shift (still fast, just moves moov atom). |
| New dependency fails to install | Low | Mutagen is pure Python with no C extensions required. |

### Rollback Plan

If Mutagen causes any issues, the rollback is trivial:

1. Remove the `update_m4a_metadata_fast()` function.
2. Revert the route handlers to call `update_m4a_metadata()` (the ffmpeg path).
3. Remove `mutagen` from `requirements.txt`.

No data migration is needed — files written by Mutagen are standard MP4 and
fully compatible with ffprobe/ffmpeg.

---

## Appendix: File Locations Reference

| Component | File | Key Functions |
| --------- | ---- | ------------- |
| Edit Modal HTML | `static/js/views/player.js` | `renderPlayerView()` lines 163–217 |
| Open Modal | `static/js/views/player.js` | `openEditMetaModal()` lines 739–763 |
| Save Logic (frontend) | `static/js/views/player.js` | `saveMetadata()` lines 836–890 |
| Handle Release | `static/js/views/player.js` | `withReleasedPlayerHandle()` lines 794–834 |
| API Client | `static/js/app.js` | `api.updateMetadata()` lines 167–178 |
| API Client (cover) | `static/js/app.js` | `api.uploadCover()` lines 191–204 |
| Route: update metadata | `src/api/routes.py` | `update_book_metadata()` lines 580–630 |
| Route: upload cover | `src/api/routes.py` | `upload_cover()` lines 637–720 |
| Route: stream audio | `src/api/routes.py` | `stream_audio()` lines 414–483 |
| Abort event | `src/api/routes.py` | `_get_stream_abort_event()` lines 135–140 |
| Encoder: update (slow) | `src/core/encoder.py` | `update_m4a_metadata()` lines 583–671 |
| Encoder: write metadata | `src/core/encoder.py` | `_write_ffmetadata()` lines 127–178 |
| Encoder: read metadata | `src/core/encoder.py` | `read_m4a_metadata()` lines 403–472 |
| Encoder: file replace | `src/core/encoder.py` | `_replace_with_retries()` lines 267–284 |
| Encoder: Windows handles | `src/core/encoder.py` | `_force_close_file_handles_windows()` lines 287–391 |
| Library Manager | `src/core/library.py` | `LibraryManager.get_book()` lines 80–132 |
| Book Files | `src/core/book_files.py` | `find_primary_m4a_path()` lines 41–59 |
| Schema | `src/models/schemas.py` | `UpdateMetadataRequest` lines 68–72 |
