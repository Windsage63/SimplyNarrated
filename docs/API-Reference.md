# SimplyNarrated API Reference

Base URL: `/api`

## Overview

The API supports upload, conversion job lifecycle, voice previews, playback/bookmarks, and library/book metadata management.

## Conventions

- `book_id` must match UUID-like format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) for all book routes.
- Audio output is currently MP3 only.
- Common error codes: `400` validation, `404` not found, `413` file too large, `500` server/internal state.

## Endpoints

### File Management

#### Upload File

- **Method**: `POST`
- **Path**: `/upload`
- **Body**: `multipart/form-data` with `file`
- **Supports**: `.txt`, `.md`, `.pdf`, `.zip` (Gutenberg HTML) (max 50MB)
- **ZIP Behavior**:
  - Selects the largest `.html`/`.htm` file in the archive as the narration source.
  - Removes Gutenberg header/footer boilerplate before chapter splitting.
  - Attempts cover extraction from image filenames containing `cover`.
- **Response**:

  ```json
  {
    "job_id": "uuid-string",
    "filename": "book.txt",
    "file_size": 1024000,
    "estimated_time": "~5 minutes",
    "chapters_detected": 3
  }
  ```

### Job Management

#### Start Generation

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

#### Get Job Status

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
    "activity_log": []
  }
  ```

#### Cancel Job

- **Method**: `POST`
- **Path**: `/cancel/{job_id}`
- **Behavior**: Cancels queued or in-progress jobs.

### TTS and Voices

#### List Voices

- **Method**: `GET`
- **Path**: `/voices`

#### Get Voice Sample

- **Method**: `GET`
- **Path**: `/voice-sample/{voice_id}`
- **Response**: `audio/mpeg`

### Library

- UI includes a `Get More Books` action in the dashboard header that opens Project Gutenberg after showing a brief download-format tip.

#### Get Library

- **Method**: `GET`
- **Path**: `/library`
- **Response** includes `books`, `total`, `in_progress`.

#### Get Book Details

- **Method**: `GET`
- **Path**: `/book/{book_id}`
- **Response**: Book metadata and chapter list.

#### Update Book Metadata

- **Method**: `PATCH`
- **Path**: `/book/{book_id}`
- **Body**:

  ```json
  {
    "title": "New Title",
    "author": "New Author"
  }
  ```

#### Delete Book

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

### Playback and Bookmarks

#### Stream Chapter Audio

- **Method**: `GET`
- **Path**: `/audio/{book_id}/{chapter}`
- **Response**: `audio/mpeg`

#### Get Chapter Text

- **Method**: `GET`
- **Path**: `/text/{book_id}/{chapter}`

#### Save Bookmark

- **Method**: `POST`
- **Path**: `/bookmark`
- **Query**: `book_id`, `chapter`, `position`

#### Get Bookmark

- **Method**: `GET`
- **Path**: `/bookmark/{book_id}`
- **Response**: stored bookmark or default `{ "chapter": 1, "position": 0.0 }`

### Cover Images

#### Upload Cover

- **Method**: `POST`
- **Path**: `/book/{book_id}/cover`
- **Body**: `multipart/form-data` with `file`
- **Supports**: JPG/PNG, max 5MB
- **Response**:

  ```json
  {
    "status": "uploaded",
    "cover_url": "/api/book/{book_id}/cover"
  }
  ```

#### Get Cover

- **Method**: `GET`
- **Path**: `/book/{book_id}/cover`
- **Response**: `image/jpeg` or `image/png`
