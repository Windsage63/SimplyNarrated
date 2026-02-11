# SimplyNarrated API Reference

Base URL: `/api`

## Overview

The SimplyNarrated API provides endpoints for file upload, text-to-speech generation, job management, and library access.

## Endpoints

### File Management

#### Upload File

- **Method**: `POST`
- **Path**: `/upload`
- **Description**: Upload a document for conversion.
- **Request Body**: `multipart/form-data` with `file` field.
- **Response**:

  ```json
  {
    "job_id": "uuid-string",
    "filename": "book.txt",
    "file_size": 1024000,
    "estimated_time": "~5 minutes",
    "chapters_detected": 12
  }
  ```

### Job Management

#### Start Generation

- **Method**: `POST`
- **Path**: `/generate`
- **Description**: Start the conversion process for an uploaded file.
- **Request Body**:

  ```json
  {
    "job_id": "uuid-string",
    "narrator_voice": "af_heart",
    "speed": 1.0,
    "quality": "hd",
    "format": "mp3",
    "remove_square_bracket_numbers": false,
    "remove_paren_numbers": false
  }
  ```

#### Get Job Status

- **Method**: `GET`
- **Path**: `/status/{job_id}`
- **Description**: Get the current progress and status of a conversion job.
- **Response**:

  ```json
  {
    "job_id": "uuid-string",
    "status": "processing",
    "progress": 45.5,
    "current_chapter": 3,
    "total_chapters": 12,
    "time_remaining": "00:03:30",
    "activity_log": [...]
  }
  ```

#### Cancel Job

- **Method**: `POST`
- **Path**: `/cancel/{job_id}`
- **Description**: Cancel an in-progress conversion job.

### TTS Config

#### List Voices

- **Method**: `GET`
- **Path**: `/voices`
- **Description**: List all available Kokoro-82M voices.
- **Response**:

  ```json
  {
    "voices": [
      {
        "id": "af_heart",
        "name": "Heart",
        "description": "Warm & Expressive",
        "gender": "female"
      },
      ...
    ],
    "total": 28
  }
  ```

#### Get Voice Sample

- **Method**: `GET`
- **Path**: `/voice-sample/{voice_id}`
- **Description**: Retrieve or generate a 3-second MP3 preview for a voice.
- **Response**: `audio/mpeg` file stream.

### Library

#### Get Library

- **Method**: `GET`
- **Path**: `/library`
- **Description**: Get the list of all converted audiobooks.

#### Get Book Details

- **Method**: `GET`
- **Path**: `/book/{book_id}`
- **Description**: Get detailed information about a specific book, including chapters.

### Playback

#### Stream Audio

- **Method**: `GET`
- **Path**: `/audio/{book_id}/{chapter}`
- **Description**: Stream or download the MP3 file for a specific chapter.

#### Get Chapter Text

- **Method**: `GET`
- **Path**: `/text/{book_id}/{chapter}`
- **Description**: Get the plain-text content for a specific chapter.
- **Response**:

  ```json
  {
    "book_id": "uuid-string",
    "chapter": 1,
    "content": "Chapter text content..."
  }
  ```

#### Save Bookmark

- **Method**: `POST`
- **Path**: `/bookmark`
- **Description**: Save the current playback position.
- **Query Parameters**: `book_id` (string), `chapter` (int), `position` (float)
- **Response**:

  ```json
  {
    "status": "saved",
    "book_id": "uuid-string",
    "chapter": 1,
    "position": 120.5
  }
  ```

#### Get Bookmark

- **Method**: `GET`
- **Path**: `/bookmark/{book_id}`
- **Description**: Get the last saved playback position for a book.

### Book Management

#### Update Book Metadata

- **Method**: `PATCH`
- **Path**: `/book/{book_id}`
- **Description**: Update the title or author of a book.
- **Request Body**:

  ```json
  {
    "title": "New Title",
    "author": "New Author"
  }
  ```

#### Delete Book

- **Method**: `DELETE`
- **Path**: `/book/{book_id}`
- **Description**: Delete a book and all its files from the library.
- **Response**:

  ```json
  {
    "status": "success",
    "message": "Book deleted",
    "book_id": "uuid-string"
  }
  ```
