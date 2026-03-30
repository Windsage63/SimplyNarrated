# SimplyNarrated API Reference

> **Last synced with codebase:** 2026-03-30

Base URL: `/api`

## Overview

The API supports file upload, audiobook generation jobs, voice previews, library browsing, portability export/import, chapter text editing, per-chapter reconversion, bookmarks, and cover management.

## Conventions

  - `book_id` must match the UUID-like format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` on book-scoped routes.
  - Chapter numbers must be integers greater than or equal to `1`.
  - Audio output is currently MP3-only. The `format` field is accepted in request schemas for forward compatibility but only `"mp3"` is supported.
  - `narrator_voice` is validated against the set of known local voice IDs on both the `/generate` and `/reconvert` endpoints. Invalid voice IDs are rejected with `400`.
  - Common error codes: `400` validation, `404` not found, `413` payload too large, `500` internal state/runtime failure.
  - Internal error details are never exposed in `500` responses; generic messages are returned and full diagnostics are logged server-side.
  - The dashboard UI includes a `Get More Books` action that opens Project Gutenberg after showing a quick format tip.

## Endpoints

### Upload and Generation

#### Upload file

  - **Method**: `POST`
  - **Path**: `/upload`
  - **Body**: `multipart/form-data` with `file`
  - **Supports**: `.txt`, `.md`, `.pdf`, `.zip`
  - **Max size**: `50MB`
  - **ZIP behavior**:
    - Treats the upload as a Gutenberg-style HTML ZIP.
    - Selects the largest `.html` or `.htm` member as the narration source.
    - Rejects corrupt archives and oversized/unsafe archives.
    - Removes Gutenberg header/footer boilerplate before chapter splitting.
    - Attempts cover extraction from image filenames whose basename contains `cover`.
  - **Response**:

  ```json
  {
    "job_id": "uuid-string",
    "filename": "book.zip",
    "file_size": 1024000,
    "estimated_time": "~5 minutes",
    "chapters_detected": 3
  }
  ```

#### Start generation

  - **Method**: `POST`
  - **Path**: `/generate`
  - **Body**:

  ```json
  {
    "job_id": "uuid-string",
    "narrator_voice": "af_heart",
    "dialogue_voice": null,
    "speed": 1.0,
    "quality": "sd",
    "format": "mp3",
    "remove_square_bracket_numbers": false,
    "remove_paren_numbers": false
  }
  ```

  - **Notes**:
    - `narrator_voice` must be a valid voice ID from the `/voices` endpoint. Invalid IDs are rejected with `400`.
    - `dialogue_voice` is accepted by the schema but the active pipeline currently uses a single narrator voice.
    - `quality` presets map to MP3 bitrates: `sd=128k`, `hd=192k`, `ultra=320k`.
    - `format` is accepted for forward compatibility but only `"mp3"` is currently supported.
    - `remove_square_bracket_numbers` strips `[N]` references before synthesis.
    - `remove_paren_numbers` strips `(N)` references before synthesis.
  - **Response**:

  ```json
  {
    "status": "started",
    "job_id": "uuid-string"
  }
  ```

#### Get job status

  - **Method**: `GET`
  - **Path**: `/status/{job_id}`
  - **Response**:

  ```json
  {
    "job_id": "uuid-string",
    "status": "processing",
    "progress": 45.5,
    "current_chapter": 3,
    "total_chapters": 12,
    "time_remaining": "~2m 10s",
    "processing_rate": "120 chars/sec",
    "activity_log": [
      {
        "timestamp": "2026-03-08T20:00:00",
        "message": "Generating audio for chapter 3/12...",
        "status": "info"
      }
    ]
  }
  ```

  - **Notes**:
    - `status` is one of `pending`, `processing`, `completed`, `failed`, or `cancelled`.
    - The response includes the last `20` activity log entries.

#### Cancel job

  - **Method**: `POST`
  - **Path**: `/cancel/{job_id}`
  - **Response**:

  ```json
  {
    "status": "cancelled",
    "job_id": "uuid-string"
  }
  ```

### Voices

#### List voices

  - **Method**: `GET`
  - **Path**: `/voices`
  - **Response shape**:

  ```json
  {
    "voices": [
      {
        "id": "af_heart",
        "name": "Heart",
        "description": "American female voice",
        "sample_url": null,
        "gender": "female"
      }
    ],
    "total": 28
  }
  ```

#### Get voice sample

  - **Method**: `GET`
  - **Path**: `/voice-sample/{voice_id}`
  - **Response**: `audio/mpeg`
  - **Notes**:
    - Uses cached samples from `static/voices/audio/` when available.
    - Otherwise synthesizes and encodes a sample on demand, then caches it.

### Library

#### Get library

  - **Method**: `GET`
  - **Path**: `/library`
  - **Response shape**:

  ```json
  {
    "books": [],
    "total": 0,
    "in_progress": 0
  }
  ```

#### Get book details

  - **Method**: `GET`
  - **Path**: `/book/{book_id}`
  - **Response**: book metadata plus chapter list.
  - **Notes**:
    - Chapter entries can include `duration`, `audio_path`, `text_path`, and `completed`.
    - Books include `cover_url`, `original_filename`, `total_duration`, and `created_at` when available.

#### Update book metadata

  - **Method**: `PATCH`
  - **Path**: `/book/{book_id}`
  - **Body**:

  ```json
  {
    "title": "New Title",
    "author": "New Author"
  }
  ```

  - **Response**:

  ```json
  {
    "status": "updated",
    "book_id": "uuid-string",
    "title": "New Title",
    "author": "New Author"
  }
  ```

  - **Notes**:
    - Existing chapter MP3 files are retagged after title or author changes so embedded ID3 album and artist metadata stay in sync.

#### Delete book

  - **Method**: `DELETE`
  - **Path**: `/book/{book_id}`
  - **Response**:

  ```json
  {
    "status": "success",
    "message": "Book deleted",
    "book_id": "uuid-string"
  }
  ```

  - **Notes**:
    - Deletion can fail with `500` if files are in use; the API asks the caller to stop playback and retry.

### Portability

#### Export audiobook archive

  - **Method**: `GET`
  - **Path**: `/book/{book_id}/export`
  - **Response**: `application/zip`
  - **Notes**:
    - Returns a temporary portability archive for download.
    - The archive contains `export_manifest.json`, `metadata.json`, chapter MP3 files, chapter text files, and optional `bookmarks.json`, `cover.jpg`/`cover.png`, and original source files.

#### Import audiobook archive

  - **Method**: `POST`
  - **Path**: `/library/import`
  - **Body**: `multipart/form-data` with `file`
  - **Supports**: `.zip` archives produced by SimplyNarrated export
  - **Max size**: `1GB`
  - **Response**:

  ```json
  {
    "status": "imported",
    "book_id": "uuid-string",
    "title": "Imported Audiobook",
    "total_chapters": 12,
    "id_remapped": false
  }
  ```

  - **Notes**:
    - Rejects non-SimplyNarrated archives, corrupt ZIPs, duplicate/unsafe members, or archives missing required files.
    - `id_remapped` becomes `true` when the imported archive ID is invalid or already exists locally.

### Chapter Audio and Text

#### Stream chapter audio

  - **Method**: `GET`
  - **Path**: `/audio/{book_id}/{chapter}`
  - **Response**: `audio/mpeg`

#### Get chapter text

  - **Method**: `GET`
  - **Path**: `/text/{book_id}/{chapter}`
  - **Response**:

  ```json
  {
    "book_id": "uuid-string",
    "chapter": 1,
    "content": "Chapter text..."
  }
  ```

#### Update chapter text

  - **Method**: `PUT`
  - **Path**: `/book/{book_id}/chapter/{chapter}/text`
  - **Body**:

  ```json
  {
    "content": "Corrected chapter text."
  }
  ```

  - **Response**:

  ```json
  {
    "status": "updated",
    "book_id": "uuid-string",
    "chapter": 1,
    "content_length": 23
  }
  ```

  - **Notes**:
    - The content is trimmed server-side.
    - Blank chapter content is rejected with `400`.

#### Reconvert a chapter

  - **Method**: `POST`
  - **Path**: `/book/{book_id}/chapter/{chapter}/reconvert`
  - **Body**:

  ```json
  {
    "narrator_voice": "af_heart",
    "speed": 1.0,
    "quality": "sd",
    "format": "mp3"
  }
  ```

  - **Response**:

  ```json
  {
    "status": "queued",
    "job_id": "uuid-string",
    "book_id": "uuid-string",
    "chapter": 1
  }
  ```

  - **Notes**:
    - Uses the saved `chapter_XX.txt` file as the source text.
    - If a field is omitted, the reconvert job falls back to the book metadata value.
    - If `narrator_voice` is provided, it is validated against known voice IDs (`400` on invalid).
    - Reconversion is MP3-only and rewrites chapter metadata/duration after replacing the audio file.
    - Reconverted MP3s receive ID3 title/album/artist/track tags and embedded cover art when present.
    - The audio file is replaced using an atomic swap with retry logic to handle temporary file locks (e.g. active playback on Windows).

### Bookmarks

#### Save bookmark

  - **Method**: `POST`
  - **Path**: `/bookmark`
  - **Query parameters**: `book_id`, `chapter`, `position`
  - **Response**:

  ```json
  {
    "status": "saved",
    "book_id": "uuid-string",
    "chapter": 2,
    "position": 33.5
  }
  ```

  - **Notes**:
    - `chapter` must be between `1` and the book's `total_chapters`.
    - `position` must be non-negative.
    - Invalid bookmark values are rejected with `400`.

#### Get bookmark

  - **Method**: `GET`
  - **Path**: `/bookmark/{book_id}`
  - **Response**:

  ```json
  {
    "chapter": 2,
    "position": 33.5,
    "updated_at": "2026-03-08T20:00:00"
  }
  ```

  - **Default when none exists**:

  ```json
  {
    "chapter": 1,
    "position": 0.0
  }
  ```

### Cover Images

#### Upload cover

  - **Method**: `POST`
  - **Path**: `/book/{book_id}/cover`
  - **Body**: `multipart/form-data` with `file`
  - **Supports**: `image/jpeg`, `image/png`
  - **Max size**: `5MB`
  - **Response**:

  ```json
  {
    "status": "uploaded",
    "cover_url": "/api/book/{book_id}/cover"
  }
  ```

  - **Notes**:
    - Uploading a new cover retags existing chapter MP3 files so embedded artwork stays in sync with the stored cover.

#### Get cover

  - **Method**: `GET`
  - **Path**: `/book/{book_id}/cover`
  - **Response**: `image/jpeg` or `image/png`
