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

import asyncio
import io
import json
import math
import os
import tempfile
import uuid
import zipfile
from functools import partial
from typing import Annotated
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Path, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from src.models.schemas import (
    UploadResponse,
    ImportResponse,
    StartGenerationResponse,
    CancelJobResponse,
    GenerateRequest,
    StatusResponse,
    VoicesResponse,
    VoiceInfo,
    LibraryResponse,
    BookInfo,
    JobStatus,
    UpdateMetadataRequest,
    UpdateMetadataResponse,
    UpdateChapterTextRequest,
    ChapterTextResponse,
    UpdateChapterTextResponse,
    ReconvertChapterRequest,
    ReconvertChapterResponse,
    SaveBookmarkResponse,
    BookmarkResponse,
    UploadCoverResponse,
    DeleteBookResponse,
)
from src.core.encoder import retag_book_mp3_files
from src.core.job_manager import get_job_manager
from src.core.library import get_library_manager
from src.core.portability import export_book_archive, import_book_archive
from src.core.tts_engine import BaseTTSModel, get_tts_manager


router = APIRouter()

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".zip"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_IMPORT_ARCHIVE_SIZE = 1024 * 1024 * 1024  # 1 GB
UUID_LIKE_PATTERN = r"^[a-f0-9-]{36}$"

# Sample quote for voice preview
SAMPLE_QUOTE = "Welcome to your audiobook library, where every story is unique and every voice has a tale to tell. Discover the magic of storytelling with our diverse range of voices, each ready to narrate your favorite books, and to bring your stories to life with the perfect voice."


def _voice_info_list(voices: list) -> list:
    """Convert model voice definitions to VoiceInfo response objects."""
    return [
        VoiceInfo(
            id=v.id,
            name=v.name,
            description=v.description,
            gender=v.gender,
            model=v.model,
        )
        for v in voices
    ]


def _get_model_or_400(model_name: str | None = None):
    manager = get_tts_manager()
    try:
        if model_name:
            return manager.get_model(model_name)
        return manager.get_active_model()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _switch_model_or_400(model_name: str):
    manager = get_tts_manager()
    try:
        return manager.switch_model(model_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _run_blocking(function, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(function, *args, **kwargs))


def _remove_existing_cover_files(book_dir: str) -> None:
    for old_cover in ("cover.jpg", "cover.png"):
        old_path = os.path.join(book_dir, old_cover)
        if os.path.exists(old_path):
            os.remove(old_path)


def _resolved_query_model(model: str | None = Query(default=None)) -> BaseTTSModel:
    return _get_model_or_400(model)


BookIdPathParam = Annotated[
    str,
    Path(min_length=36, max_length=36, pattern=UUID_LIKE_PATTERN),
]
BookIdQueryParam = Annotated[
    str,
    Query(min_length=36, max_length=36, pattern=UUID_LIKE_PATTERN),
]
JobIdPathParam = Annotated[
    str,
    Path(min_length=36, max_length=36, pattern=UUID_LIKE_PATTERN),
]
ChapterPathParam = Annotated[int, Path(ge=1)]
ChapterQueryParam = Annotated[int, Query(ge=1)]
PositionQueryParam = Annotated[float, Query(ge=0)]
ResolvedQueryModel = Annotated[BaseTTSModel, Depends(_resolved_query_model)]


async def _load_book_metadata_or_404(book_dir: str) -> dict:
    """Load metadata for a book directory, raising 404 if unavailable."""
    metadata_path = os.path.join(book_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Book not found")

    async with aiofiles.open(metadata_path, "r", encoding="utf-8") as metadata_file:
        return json.loads(await metadata_file.read())


def _ensure_chapter_exists_or_404(metadata: dict, chapter: int) -> None:
    """Ensure chapter index exists in metadata chapters list."""
    exists = any(int(ch.get("number", 0)) == chapter for ch in metadata.get("chapters", []))
    if not exists:
        raise HTTPException(status_code=404, detail="Chapter not found")


def _validate_bookmark_or_400(metadata: dict, chapter: int, position: float) -> None:
    """Validate bookmark chapter and position values."""
    total_chapters = int(metadata.get("total_chapters") or len(metadata.get("chapters", [])) or 0)
    if total_chapters > 0 and chapter > total_chapters:
        raise HTTPException(
            status_code=400,
            detail=f"Chapter {chapter} exceeds book chapter count ({total_chapters})",
        )


def _cleanup_file(path: str) -> None:
    """Best-effort cleanup for temporary files."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _estimate_chapters(file_ext: str, content: bytes, file_size: int) -> int:
    """Estimate likely chapter count during upload for early UX feedback."""
    try:
        if file_ext == ".txt":
            text = content.decode("utf-8", errors="ignore")
            words = len(text.split())
            return max(1, math.ceil(words / 4000))
        if file_ext == ".zip":
            # ZIP with HTML: estimate from uncompressed HTML size
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


@router.post("/generate", response_model=StartGenerationResponse)
async def start_generation(request: GenerateRequest, background_tasks: BackgroundTasks):
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

    model = _get_model_or_400(request.model)

    # Validate narrator_voice against the selected model
    valid_voice_ids = {v.id for v in model.get_voices()}
    if request.narrator_voice not in valid_voice_ids:
        raise HTTPException(status_code=400, detail="Invalid narrator voice")

    # Convert request to config dict
    config = {
        "model": model.name,
        "narrator_voice": request.narrator_voice,
    }

    # Import process function here to avoid circular imports
    from src.core.pipeline import process_book

    # Start job in background
    success = await job_manager.start_job(job.id, config, process_book)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to start job")

    return {"status": "started", "job_id": job.id}


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: JobIdPathParam):
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


@router.post("/cancel/{job_id}", response_model=CancelJobResponse)
async def cancel_job(job_id: JobIdPathParam):
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


@router.get("/models")
async def list_models():
    """List registered TTS models and the currently active model."""
    manager = get_tts_manager()
    active_model = manager.get_active_model()
    return {
        "models": manager.get_available_model_names(),
        "active_model": active_model.name,
    }


@router.post("/models/switch")
async def switch_model(payload: dict):
    """Switch the active TTS model."""
    model_name = payload.get("model") if isinstance(payload, dict) else None
    if not model_name or not isinstance(model_name, str):
        raise HTTPException(status_code=400, detail="Model is required")

    model = _switch_model_or_400(model_name)
    return {"status": "ok", "active_model": model.name}


@router.get("/voices", response_model=VoicesResponse)
async def list_voices(tts_model: ResolvedQueryModel):
    """
    List all available voices for TTS.
    """
    voices = _voice_info_list(tts_model.get_voices())
    return VoicesResponse(
        voices=voices,
        total=len(voices),
    )


@router.get("/voice-sample/{voice_id}")
async def get_voice_sample(voice_id: str, tts_model: ResolvedQueryModel):
    """
    Generate or retrieve a voice sample for preview.
    Uses cached samples if available, otherwise generates on-demand.
    """
    from src.core.encoder import encode_audio, EncoderSettings
    import logging

    logger = logging.getLogger(__name__)

    model_name = tts_model.name

    # Validate voice_id
    valid_voice_ids = [v.id for v in tts_model.get_voices()]
    if voice_id not in valid_voice_ids:
        raise HTTPException(status_code=400, detail="Invalid voice ID")

    # Check for cached sample (mp3 only)
    cache_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "static", "voices", "audio", model_name
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
        quote = SAMPLE_QUOTE
        logger.info("Generating voice sample for %s: '%.50s...'", voice_id, quote)

        # Run TTS in thread pool to not block
        loop = asyncio.get_running_loop()
        audio, sample_rate = await loop.run_in_executor(
            None, lambda: tts_model.generate_sample(voice_id)
        )

        if audio is None or len(audio) == 0:
            raise HTTPException(
                status_code=500, detail="TTS engine returned empty audio"
            )

        # Encode to MP3
        cache_path_mp3 = os.path.join(cache_dir, f"{voice_id}.mp3")
        settings = EncoderSettings(bitrate="128k")

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
    except Exception:
        logger.exception("Failed to generate voice sample for %s", voice_id)
        raise HTTPException(status_code=500, detail="Failed to generate voice sample")


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
async def get_book(book_id: BookIdPathParam):
    """
    Get details for a specific book.
    """
    library = get_library_manager()
    book = library.get_book(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return book


@router.get("/book/{book_id}/export")
async def export_book(book_id: BookIdPathParam):
    """Create and download a portability ZIP for a book."""
    library = get_library_manager()

    try:
        archive_path, download_name = export_book_archive(library, book_id)
    except FileNotFoundError as exc:
        detail = str(exc) or "Book not found"
        status_code = 404 if "metadata" in detail.lower() else 500
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=download_name,
        background=BackgroundTask(_cleanup_file, archive_path),
    )


@router.post("/library/import", response_model=ImportResponse)
async def import_library_book(file: UploadFile = File(...)):
    """Import a portability ZIP generated by SimplyNarrated export."""
    filename = file.filename or "audiobook.zip"
    if os.path.splitext(filename)[1].lower() != ".zip":
        raise HTTPException(status_code=400, detail="Only .zip audiobook archives are supported")

    temp_fd, temp_path = tempfile.mkstemp(prefix="simplynarrated-import-", suffix=".zip")
    os.close(temp_fd)
    total_read = 0

    try:
        async with aiofiles.open(temp_path, "wb") as temp_file:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_read += len(chunk)
                if total_read > MAX_IMPORT_ARCHIVE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Archive too large. Maximum size: {MAX_IMPORT_ARCHIVE_SIZE // (1024 * 1024)}MB",
                    )
                await temp_file.write(chunk)

        library = get_library_manager()
        try:
            result = import_book_archive(library, temp_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return ImportResponse(**result)
    finally:
        await file.close()
        _cleanup_file(temp_path)


@router.get("/audio/{book_id}/{chapter}")
async def stream_audio(book_id: BookIdPathParam, chapter: ChapterPathParam):
    """
    Stream a chapter's MP3 audio file.
    """
    job_manager = get_job_manager()
    library = get_library_manager()

    # MP3 only
    extensions = [(".mp3", "audio/mpeg")]

    # 1. Check if this is an active job
    job = job_manager.get_job(book_id)
    if job and job.output_dir:
        for ext, media_type in extensions:
            audio_path = os.path.join(job.output_dir, f"chapter_{chapter:02d}{ext}")
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                return FileResponse(
                    audio_path,
                    media_type=media_type,
                    filename=f"chapter_{chapter:02d}{ext}",
                )

    # 2. Check library path
    book_dir = library.get_book_dir(book_id)
    for ext, media_type in extensions:
        audio_path = os.path.join(book_dir, f"chapter_{chapter:02d}{ext}")
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            return FileResponse(
                audio_path,
                media_type=media_type,
                filename=f"chapter_{chapter:02d}{ext}",
            )

    raise HTTPException(status_code=404, detail="Audio file not found")


@router.get("/text/{book_id}/{chapter}", response_model=ChapterTextResponse)
async def get_chapter_text(book_id: BookIdPathParam, chapter: ChapterPathParam):
    """
    Get the text content for a specific chapter.
    """
    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    text_path = os.path.join(book_dir, f"chapter_{chapter:02d}.txt")

    if not os.path.exists(text_path):
        raise HTTPException(status_code=404, detail="Chapter text not found")

    async with aiofiles.open(text_path, "r", encoding="utf-8") as f:
        content = await f.read()

    return {"book_id": book_id, "chapter": chapter, "content": content}


@router.put(
    "/book/{book_id}/chapter/{chapter}/text",
    response_model=UpdateChapterTextResponse,
)
async def update_chapter_text(
    book_id: BookIdPathParam,
    chapter: ChapterPathParam,
    request: UpdateChapterTextRequest,
):
    """
    Update generated text for a specific chapter.
    """
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Chapter content cannot be empty")

    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    metadata = await _load_book_metadata_or_404(book_dir)
    _ensure_chapter_exists_or_404(metadata, chapter)

    text_path = os.path.join(book_dir, f"chapter_{chapter:02d}.txt")
    async with aiofiles.open(text_path, "w", encoding="utf-8") as chapter_file:
        await chapter_file.write(request.content)

    return {
        "status": "updated",
        "book_id": book_id,
        "chapter": chapter,
        "content_length": len(request.content),
    }


@router.post(
    "/book/{book_id}/chapter/{chapter}/reconvert",
    response_model=ReconvertChapterResponse,
)
async def reconvert_chapter(
    book_id: BookIdPathParam,
    chapter: ChapterPathParam,
    request: ReconvertChapterRequest,
):
    """
    Queue reconversion for a single chapter using the current chapter text file.
    """
    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    metadata = await _load_book_metadata_or_404(book_dir)
    _ensure_chapter_exists_or_404(metadata, chapter)

    # Validate narrator_voice if provided
    if request.narrator_voice is not None:
        selected_model = request.model or metadata.get("model") or "kokoro"
        model = _get_model_or_400(selected_model)
        valid_voice_ids = {v.id for v in model.get_voices()}
        if request.narrator_voice not in valid_voice_ids:
            raise HTTPException(status_code=400, detail="Invalid narrator voice")
    else:
        model = _get_model_or_400(request.model or metadata.get("model") or "kokoro")

    text_path = os.path.join(book_dir, f"chapter_{chapter:02d}.txt")
    if not os.path.exists(text_path):
        raise HTTPException(status_code=404, detail="Chapter text not found")

    job_manager = get_job_manager()
    existing_job = job_manager.find_active_reconvert_job(book_id, chapter)
    if existing_job:
        return {
            "status": "processing" if existing_job.status == JobStatus.PROCESSING else "queued",
            "job_id": existing_job.id,
            "book_id": book_id,
            "chapter": chapter,
        }

    chapter_job = job_manager.create_job(
        filename=f"chapter_{chapter:02d}_reconvert",
        file_path=text_path,
    )

    from src.core.chapter_reconvert import process_chapter_reconvert_job

    config = {
        "job_type": "chapter_reconvert",
        "book_id": book_id,
        "chapter_number": chapter,
        "book_dir": book_dir,
        "output_dir": book_dir,
        "model": model.name,
        "narrator_voice": request.narrator_voice,
    }

    success = await job_manager.start_job(chapter_job.id, config, process_chapter_reconvert_job)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to queue chapter reconversion")

    return {
        "status": "queued",
        "job_id": chapter_job.id,
        "book_id": book_id,
        "chapter": chapter,
    }


@router.post("/bookmark", response_model=SaveBookmarkResponse)
async def save_bookmark(
    book_id: BookIdQueryParam,
    chapter: ChapterQueryParam,
    position: PositionQueryParam,
):
    """
    Save a playback bookmark for a book.
    """
    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    metadata = await _load_book_metadata_or_404(book_dir)
    _validate_bookmark_or_400(metadata, chapter, position)

    success = library.save_bookmark(book_id, chapter, position)

    if not success:
        raise HTTPException(status_code=404, detail="Book not found")

    return {
        "status": "saved",
        "book_id": book_id,
        "chapter": chapter,
        "position": position,
    }


@router.get("/bookmark/{book_id}", response_model=BookmarkResponse)
async def get_bookmark(book_id: BookIdPathParam):
    """
    Get the user's playback position for a book.
    """
    library = get_library_manager()
    bookmark = library.get_bookmark(book_id)

    if not bookmark:
        return {"chapter": 1, "position": 0.0}

    return {
        "chapter": bookmark.chapter,
        "position": bookmark.position,
        "updated_at": bookmark.updated_at,
    }


@router.patch("/book/{book_id}", response_model=UpdateMetadataResponse)
async def update_book_metadata(book_id: BookIdPathParam, request: UpdateMetadataRequest):
    """
    Update metadata (title, author) for a specific book.
    """
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    await _load_book_metadata_or_404(book_dir)
    success = await _run_blocking(library.update_book_metadata, book_id, updates)

    if not success:
        raise HTTPException(status_code=404, detail="Book not found")

    metadata = await _load_book_metadata_or_404(book_dir)
    await _run_blocking(retag_book_mp3_files, book_dir, metadata)

    return {"status": "updated", "book_id": book_id, **updates}


MAX_COVER_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _detect_cover_extension(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    return None


@router.post("/book/{book_id}/cover", response_model=UploadCoverResponse)
async def upload_cover(book_id: BookIdPathParam, file: UploadFile = File(...)):
    """
    Upload a cover image for a book.
    Accepts .jpg/.png files up to 5 MB.
    """
    # Validate file extension
    filename = file.filename or "cover"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_COVER_EXTENSIONS:
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

    save_ext = _detect_cover_extension(content)
    if save_ext is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file. Only JPG and PNG images are allowed.",
        )

    library = get_library_manager()
    book_dir = library.get_book_dir(book_id)
    if not os.path.exists(os.path.join(book_dir, "metadata.json")):
        raise HTTPException(status_code=404, detail="Book not found")

    # Remove any existing cover files
    await _run_blocking(_remove_existing_cover_files, book_dir)

    cover_filename = f"cover{save_ext}"
    cover_path = os.path.join(book_dir, cover_filename)

    async with aiofiles.open(cover_path, "wb") as f:
        await f.write(content)

    # Update metadata
    cover_url = f"/api/book/{book_id}/cover"
    await _run_blocking(library.update_book_metadata, book_id, {"cover_url": cover_url})
    metadata = await _load_book_metadata_or_404(book_dir)
    await _run_blocking(retag_book_mp3_files, book_dir, metadata)

    return {"status": "uploaded", "cover_url": cover_url}


@router.get("/book/{book_id}/cover")
async def get_cover(book_id: BookIdPathParam):
    """
    Serve the cover image for a book.
    """
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


@router.delete("/book/{book_id}", response_model=DeleteBookResponse)
async def delete_book(book_id: BookIdPathParam):
    """
    Delete a book from the library.
    """
    library = get_library_manager()

    # Check existence separate from deletion success
    book_dir = library.get_book_dir(book_id)
    if not os.path.exists(book_dir):
        raise HTTPException(status_code=404, detail="Book not found")

    success = await _run_blocking(library.delete_book, book_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="The book files are currently in use. Please stop the player and try again.",
        )

    return {"status": "success", "message": "Book deleted", "book_id": book_id}
