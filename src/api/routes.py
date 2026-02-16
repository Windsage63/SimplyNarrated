"""
@fileoverview SimplyNarrated - API Routes, All REST API endpoints for the application
@author Timothy Mallory <windsage@live.com>
@license Apache-2.0
@copyright 2026 Timothy Mallory <windsage@live.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import re
import uuid
import asyncio
import math
import logging
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from src.models.schemas import (
    UploadResponse,
    GenerateRequest,
    StatusResponse,
    VoicesResponse,
    VoiceInfo,
    LibraryResponse,
    BookInfo,
    JobStatus,
    UpdateMetadataRequest,
)
from src.core.job_manager import get_job_manager
from src.core.library import get_library_manager
from src.core.tts_engine import PRESET_VOICES
from src.core.encoder import read_m4a_metadata, update_m4a_metadata


router = APIRouter()
logger = logging.getLogger(__name__)
_stream_abort_events: dict[str, asyncio.Event] = {}

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".zip"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Sample quote for voice preview
SAMPLE_QUOTE = "Welcome to your audiobook library, where every story is unique and every voice has a tale to tell. Discover the magic of storytelling with our diverse range of voices, each ready to narrate your favorite books, and to bring your stories to life with the perfect voice."
BOOK_ID_PATTERN = re.compile(r"^[a-f0-9-]{36}$")


def _get_available_voices() -> list:
    """Convert PRESET_VOICES to VoiceInfo objects for API responses."""
    return [
        VoiceInfo(
            id=v.id,
            name=v.name,
            description=v.description,
            gender=v.gender,
        )
        for v in PRESET_VOICES
    ]


# Cache the converted list
AVAILABLE_VOICES = _get_available_voices()


def _validate_book_id_or_400(book_id: str) -> None:
    """Validate UUID-like book IDs to prevent path traversal."""
    if not BOOK_ID_PATTERN.match(book_id):
        raise HTTPException(status_code=400, detail="Invalid book ID format")


def _sanitize_book_filename(title: str, fallback: str) -> str:
    candidate = re.sub(r"[\\/:*?\"<>|]+", " ", title or "")
    candidate = re.sub(r"\s+", " ", candidate).strip().strip(".")
    return candidate or fallback


def _load_book_metadata(book_dir: str) -> dict:
    m4a_files = []
    if os.path.isdir(book_dir):
        for name in os.listdir(book_dir):
            lower = name.lower()
            if not lower.endswith(".m4a"):
                continue
            if ".metadata." in lower or ".tmp." in lower or lower.endswith(".tmp.m4a"):
                continue
            path = os.path.join(book_dir, name)
            m4a_files.append((name, os.path.getmtime(path), path))

    m4a_files.sort(key=lambda item: (item[1], item[0].lower()), reverse=True)
    if not m4a_files:
        raise HTTPException(status_code=404, detail="Book not found")

    book_file = m4a_files[0][0]
    book_path = m4a_files[0][2]
    metadata = read_m4a_metadata(book_path)
    metadata["book_file"] = book_file
    metadata["transcript_path"] = metadata.get("transcript_path") or "transcript.txt"
    return metadata


def _find_cover_path(book_dir: str) -> str | None:
    for candidate in ("cover.jpg", "cover.png"):
        path = os.path.join(book_dir, candidate)
        if os.path.exists(path):
            return path
    return None


def _estimate_chapters(file_ext: str, content: bytes, file_size: int) -> int:
    """Estimate likely chapter count during upload for early UX feedback."""
    try:
        if file_ext in {".txt", ".md"}:
            text = content.decode("utf-8", errors="ignore")
            words = len(text.split())
            return max(1, math.ceil(words / 4000))
        if file_ext == ".zip":
            # ZIP with HTML: estimate from uncompressed HTML size
            import io
            import zipfile
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    html_sizes = [
                        info.file_size
                        for info in zf.infolist()
                        if not info.is_dir()
                        and info.filename.lower().endswith((".html", ".htm"))
                    ]
                    if html_sizes:
                        largest = max(html_sizes)
                        return max(1, math.ceil(largest / (20 * 1024)))
            except Exception:
                pass
    except Exception:
        pass

    # Conservative fallback when content is binary (e.g., PDF): ~20KB per chapter.
    return max(1, math.ceil(file_size / (20 * 1024)))


def _get_stream_abort_event(book_id: str) -> asyncio.Event:
    event = _stream_abort_events.get(book_id)
    if event is None:
        event = asyncio.Event()
        _stream_abort_events[book_id] = event
    return event


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file for conversion.
    Returns a job_id for tracking the conversion.
    """
    # Validate file extension
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    # Read file content with size limit to prevent memory exhaustion
    content = await file.read(MAX_FILE_SIZE + 1)
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Save file to uploads directory
    job_manager = get_job_manager()
    file_id = str(uuid.uuid4())
    file_path = os.path.join(job_manager.uploads_dir, f"{file_id}{ext}")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create job
    job = job_manager.create_job(filename, file_path)

    # Estimate conversion time (rough: 1 min per 10KB)
    estimated_minutes = max(1, file_size // (10 * 1024))
    chapters_detected = _estimate_chapters(ext, content, file_size)

    return UploadResponse(
        job_id=job.id,
        filename=filename,
        file_size=file_size,
        estimated_time=f"~{estimated_minutes} minutes",
        chapters_detected=chapters_detected,
    )


@router.post("/generate")
async def start_generation(request: GenerateRequest):
    """
    Start audiobook generation for an uploaded file.
    """
    job_manager = get_job_manager()
    job = job_manager.get_job(request.job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be started. Current status: {job.status}",
        )

    # Convert request to config dict
    config = {
        "narrator_voice": request.narrator_voice,
        "dialogue_voice": request.dialogue_voice,
        "speed": request.speed,
        "quality": request.quality.value,
        "format": request.format.value,
        "remove_square_bracket_numbers": request.remove_square_bracket_numbers,
        "remove_paren_numbers": request.remove_paren_numbers,
    }

    # Import process function here to avoid circular imports
    from src.core.pipeline import process_book

    # Start job in background
    success = await job_manager.start_job(job.id, config, process_book)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to start job")

    return {"status": "started", "job_id": job.id}


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """
    Get the current status of a conversion job.
    """
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return StatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_chapter=job.current_chapter,
        total_chapters=job.total_chapters,
        time_remaining=job_manager.get_time_remaining(job),
        processing_rate=job_manager.get_processing_rate(job),
        activity_log=job.activity_log[-20:],  # Last 20 entries
    )


@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel an in-progress conversion job.
    """
    job_manager = get_job_manager()
    success = job_manager.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=400, detail="Job cannot be cancelled (not in progress)"
        )

    return {"status": "cancelled", "job_id": job_id}


@router.get("/voices", response_model=VoicesResponse)
async def list_voices():
    """
    List all available voices for TTS.
    """
    return VoicesResponse(
        voices=AVAILABLE_VOICES,
        total=len(AVAILABLE_VOICES),
    )


@router.get("/voice-sample/{voice_id}")
async def get_voice_sample(voice_id: str):
    """
    Generate or retrieve a voice sample for preview.
    Uses cached samples if available, otherwise generates on-demand.
    """
    from src.core.tts_engine import get_tts_engine
    from src.core.encoder import encode_audio, EncoderSettings
    import logging

    logger = logging.getLogger(__name__)

    # Validate voice_id
    valid_voice_ids = [v.id for v in AVAILABLE_VOICES]
    if voice_id not in valid_voice_ids:
        raise HTTPException(status_code=400, detail="Invalid voice ID")

    # Check for cached sample (mp3 only)
    cache_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "static", "voices", "audio"
    )
    os.makedirs(cache_dir, exist_ok=True)

    cache_path = os.path.join(cache_dir, f"{voice_id}.mp3")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        return FileResponse(
            cache_path,
            media_type="audio/mpeg",
            filename=f"{voice_id}_sample.mp3",
        )

    # Generate new sample
    try:
        tts_engine = get_tts_engine()
        quote = SAMPLE_QUOTE
        logger.info(f"Generating voice sample for {voice_id}: '{quote[:50]}...'")

        # Run TTS in thread pool to not block
        loop = asyncio.get_running_loop()
        audio, sample_rate = await loop.run_in_executor(
            None, lambda: tts_engine.generate_speech(quote, voice_id, speed=1.0)
        )

        if audio is None or len(audio) == 0:
            raise HTTPException(
                status_code=500, detail="TTS engine returned empty audio"
            )

        # Encode to MP3
        cache_path_mp3 = os.path.join(cache_dir, f"{voice_id}.mp3")
        settings = EncoderSettings(format="mp3", bitrate="128k")

        actual_path = await asyncio.get_running_loop().run_in_executor(
            None, lambda: encode_audio(audio, sample_rate, cache_path_mp3, settings)
        )

        if not os.path.exists(actual_path) or os.path.getsize(actual_path) == 0:
            raise HTTPException(status_code=500, detail="Failed to encode audio file")

        return FileResponse(
            actual_path,
            media_type="audio/mpeg",
            filename=f"{voice_id}_sample.mp3",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate voice sample for {voice_id}")
        raise HTTPException(status_code=500, detail=f"Failed to generate sample: {e}")


@router.get("/library", response_model=LibraryResponse)
async def get_library():
    """
    Get the user's audiobook library.
    """
    library = get_library_manager()
    job_manager = get_job_manager()

    books = library.scan_library()
    in_progress = job_manager.count_processing_jobs()

    return LibraryResponse(
        books=books,
        total=len(books),
        in_progress=in_progress,
    )


@router.get("/book/{book_id}", response_model=BookInfo)
async def get_book(book_id: str):
    """
    Get details for a specific book.
    """
    _validate_book_id_or_400(book_id)

    library = get_library_manager()
    book = library.get_book(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return book


@router.get("/audio/{book_id}")
async def stream_audio(book_id: str, request: Request):
    """
    Stream the completed audiobook file.
    """
    _validate_book_id_or_400(book_id)
    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    metadata = _load_book_metadata(book_dir)
    book_file = metadata.get("book_file")
    if not book_file:
        raise HTTPException(status_code=404, detail="Audiobook file not found")

    audio_path = os.path.join(book_dir, book_file)
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise HTTPException(status_code=404, detail="Audiobook file not found")

    file_size = os.path.getsize(audio_path)
    range_header = request.headers.get("range")
    start = 0
    end = file_size - 1
    status_code = 200
    headers = {"Accept-Ranges": "bytes"}

    if range_header:
        try:
            units, range_spec = range_header.strip().split("=", 1)
            if units.lower() != "bytes":
                raise ValueError("Unsupported range unit")

            start_raw, end_raw = range_spec.split("-", 1)
            start = int(start_raw) if start_raw else 0
            end = int(end_raw) if end_raw else end

            if start < 0 or end < start or start >= file_size:
                raise ValueError("Invalid range")

            end = min(end, file_size - 1)
            status_code = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        except Exception:
            raise HTTPException(status_code=416, detail="Invalid range")

    content_length = end - start + 1
    headers["Content-Length"] = str(content_length)

    abort_event = _get_stream_abort_event(book_id)

    async def iter_file():
        chunk_size = 64 * 1024
        remaining = content_length
        with open(audio_path, "rb") as fh:
            fh.seek(start)
            while remaining > 0:
                if abort_event.is_set():
                    break
                to_read = min(chunk_size, remaining)
                data = fh.read(to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data
                await asyncio.sleep(0)

    return StreamingResponse(
        iter_file(),
        media_type="audio/mp4",
        status_code=status_code,
        headers=headers,
    )


@router.get("/book/{book_id}/download")
async def download_book(book_id: str):
    """
    Download the completed audiobook file.
    """
    _validate_book_id_or_400(book_id)

    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    metadata = _load_book_metadata(book_dir)
    book_file = metadata.get("book_file")
    if not book_file:
        raise HTTPException(status_code=404, detail="Audiobook file not found")

    audio_path = os.path.join(book_dir, book_file)
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise HTTPException(status_code=404, detail="Audiobook file not found")

    download_name = f"{_sanitize_book_filename(metadata.get('title', ''), book_id)}.m4a"

    return FileResponse(
        audio_path,
        media_type="audio/mp4",
        filename=download_name,
    )


@router.get("/transcript/{book_id}")
async def get_transcript(book_id: str):
    """
    Get full transcript text content and chapter anchors.
    """
    _validate_book_id_or_400(book_id)

    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    metadata = _load_book_metadata(book_dir)
    transcript_name = metadata.get("transcript_path") or "transcript.txt"
    text_path = os.path.join(book_dir, transcript_name)

    if not os.path.exists(text_path):
        raise HTTPException(status_code=404, detail="Transcript not found")

    async with aiofiles.open(text_path, "r", encoding="utf-8") as f:
        content = await f.read()

    return {
        "book_id": book_id,
        "content": content,
        "chapters": metadata.get("chapters", []),
    }


@router.post("/bookmark")
async def save_bookmark(book_id: str, chapter: int, position: float):
    """
    Save a playback bookmark for a book.
    """
    _validate_book_id_or_400(book_id)

    library = get_library_manager()
    success = library.save_bookmark(book_id, chapter, position)

    if not success:
        raise HTTPException(status_code=404, detail="Book not found")

    return {
        "status": "saved",
        "book_id": book_id,
        "chapter": chapter,
        "position": position,
    }


@router.get("/bookmark/{book_id}")
async def get_bookmark(book_id: str):
    """
    Get the user's playback position for a book.
    """
    _validate_book_id_or_400(book_id)

    library = get_library_manager()
    bookmark = library.get_bookmark(book_id)

    if not bookmark:
        return {"chapter": 1, "position": 0.0}

    return {
        "chapter": bookmark.chapter,
        "position": bookmark.position,
        "updated_at": bookmark.updated_at,
    }


@router.patch("/book/{book_id}")
async def update_book_metadata(book_id: str, request: UpdateMetadataRequest):
    """
    Update metadata (title, author) for a specific book.
    """
    _validate_book_id_or_400(book_id)

    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    book = library.get_book(book_id)
    book_file_path = library.get_book_audio_path(book_id)
    if not book or not book_file_path:
        raise HTTPException(status_code=404, detail="Book not found")

    new_title = updates.get("title", book.title)
    new_author = updates.get("author", book.author)

    try:
        abort_event = _get_stream_abort_event(book_id)
        abort_event.set()
        await asyncio.sleep(0.2)

        update_m4a_metadata(
            file_path=book_file_path,
            title=new_title,
            author=new_author,
            chapters=[chapter.model_dump() for chapter in book.chapters],
            cover_path=_find_cover_path(book_dir),
            custom_metadata={
                "SIMPLYNARRATED_ID": book.id,
                "SIMPLYNARRATED_CREATED_AT": book.created_at.isoformat(),
                "SIMPLYNARRATED_ORIGINAL_FILENAME": book.original_filename,
                "SIMPLYNARRATED_TRANSCRIPT_PATH": book.transcript_path,
            },
            replace_retries=40,
            retry_delay_seconds=0.25,
        )
    except (PermissionError, OSError) as e:
        raise HTTPException(
            status_code=423,
            detail=f"Failed to save metadata: {e}",
        ) from e
    finally:
        _get_stream_abort_event(book_id).clear()

    response = {"status": "updated", "book_id": book_id, "title": new_title, "author": new_author}
    return response


MAX_COVER_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_COVER_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}


@router.post("/book/{book_id}/cover")
async def upload_cover(book_id: str, file: UploadFile = File(...)):
    """
    Upload a cover image for a book.
    Accepts .jpg/.png files up to 5 MB.
    """
    _validate_book_id_or_400(book_id)

    # Validate content type
    if file.content_type not in ALLOWED_COVER_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPG and PNG images are allowed.",
        )

    # Validate file extension
    filename = file.filename or "cover"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file extension. Only .jpg and .png are allowed.",
        )

    # Read with size limit
    content = await file.read(MAX_COVER_SIZE + 1)
    if len(content) > MAX_COVER_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_COVER_SIZE // (1024 * 1024)}MB",
        )

    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    book = library.get_book(book_id)
    book_file_path = library.get_book_audio_path(book_id)
    if not book or not book_file_path:
        raise HTTPException(status_code=404, detail="Book not found")

    # Remove any existing cover files
    for old_cover in ("cover.jpg", "cover.png"):
        old_path = os.path.join(book_dir, old_cover)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Determine save extension from content type
    save_ext = ALLOWED_COVER_TYPES[file.content_type]
    cover_filename = f"cover{save_ext}"
    cover_path = os.path.join(book_dir, cover_filename)

    async with aiofiles.open(cover_path, "wb") as f:
        await f.write(content)

    cover_url = f"/api/book/{book_id}/cover"

    try:
        abort_event = _get_stream_abort_event(book_id)
        abort_event.set()
        await asyncio.sleep(0.2)

        update_m4a_metadata(
            file_path=book_file_path,
            title=book.title,
            author=book.author,
            chapters=[chapter.model_dump() for chapter in book.chapters],
            cover_path=cover_path,
            custom_metadata={
                "SIMPLYNARRATED_ID": book.id,
                "SIMPLYNARRATED_CREATED_AT": book.created_at.isoformat(),
                "SIMPLYNARRATED_ORIGINAL_FILENAME": book.original_filename,
                "SIMPLYNARRATED_TRANSCRIPT_PATH": book.transcript_path,
            },
            replace_retries=40,
            retry_delay_seconds=0.25,
        )
    except (PermissionError, OSError) as e:
        raise HTTPException(
            status_code=423,
            detail=f"Failed to save metadata: {e}",
        ) from e
    finally:
        _get_stream_abort_event(book_id).clear()

    return {"status": "uploaded", "cover_url": cover_url}


@router.get("/book/{book_id}/cover")
async def get_cover(book_id: str):
    """
    Serve the cover image for a book.
    """
    _validate_book_id_or_400(book_id)

    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)

    # Check for cover files
    for filename, media_type in [("cover.jpg", "image/jpeg"), ("cover.png", "image/png")]:
        cover_path = os.path.join(book_dir, filename)
        if os.path.exists(cover_path) and os.path.getsize(cover_path) > 0:
            return FileResponse(
                cover_path,
                media_type=media_type,
                filename=filename,
            )

    raise HTTPException(status_code=404, detail="Cover image not found")


@router.delete("/book/{book_id}")
async def delete_book(book_id: str):
    """
    Delete a book from the library.
    """
    _validate_book_id_or_400(book_id)

    library = get_library_manager()

    # Check existence separate from deletion success
    book_dir = library.get_book_dir(book_id)
    if not os.path.exists(book_dir):
        raise HTTPException(status_code=404, detail="Book not found")

    success = library.delete_book(book_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="The book files are currently in use. Please stop the player and try again.",
        )

    return {"status": "success", "message": "Book deleted", "book_id": book_id}
