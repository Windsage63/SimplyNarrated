"""
@fileoverview BookTalk - API Routes, All REST API endpoints for the application
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
import random
import asyncio
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from src.models.schemas import (
    UploadResponse,
    GenerateRequest,
    StatusResponse,
    VoicesResponse,
    VoiceInfo,
    LibraryResponse,
    BookInfo,
    JobStatus,
)
from src.core.job_manager import get_job_manager
from src.core.library import get_library_manager
from src.core.tts_engine import PRESET_VOICES


router = APIRouter()

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".md", ".epub", ".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Sample quotes for voice previews - short, varied content
SAMPLE_QUOTES = [
    "The quick brown fox jumps over the lazy dog.",
    "To be, or not to be, that is the question.",
    "It was the best of times, it was the worst of times.",
    "Hello! I'm your narrator for this audiobook adventure.",
    "In a hole in the ground there lived a hobbit.",
    "All happy families are alike; each unhappy family is unhappy in its own way.",
]


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

    return UploadResponse(
        job_id=job.id,
        filename=filename,
        file_size=file_size,
        estimated_time=f"~{estimated_minutes} minutes",
        chapters_detected=0,  # Will be updated after parsing
    )


@router.post("/generate")
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
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "voices", "audio")
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
        quote = random.choice(SAMPLE_QUOTES)
        logger.info(f"Generating voice sample for {voice_id}: '{quote[:50]}...'")

        # Run TTS in thread pool to not block
        loop = asyncio.get_event_loop()
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

        actual_path = await loop.run_in_executor(
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
    library = get_library_manager()
    book = library.get_book(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return book


@router.get("/audio/{book_id}/{chapter}")
async def stream_audio(book_id: str, chapter: int):
    """
    Stream or download a chapter's audio file.
    Supports both .mp3 and .wav formats.
    """
    # Validate book_id format to prevent path traversal
    if not re.match(r"^[a-f0-9-]{36}$", book_id):
        raise HTTPException(status_code=400, detail="Invalid book ID format")

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


@router.post("/bookmark")
async def save_bookmark(book_id: str, chapter: int, position: float):
    """
    Save a playback bookmark for a book.
    """
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
    library = get_library_manager()
    bookmark = library.get_bookmark(book_id)

    if not bookmark:
        return {"chapter": 1, "position": 0.0}

    return {
        "chapter": bookmark.chapter,
        "position": bookmark.position,
        "updated_at": bookmark.updated_at,
    }


@router.delete("/book/{book_id}")
async def delete_book(book_id: str):
    """
    Delete a book from the library.
    """
    # Validate book_id format to prevent path traversal
    if not re.match(r"^[a-f0-9-]{36}$", book_id.lower()):
        raise HTTPException(status_code=400, detail="Invalid book ID format")

    library = get_library_manager()
    
    # Check existence separate from deletion success
    book_dir = library.get_book_dir(book_id)
    if not os.path.exists(book_dir):
        raise HTTPException(status_code=404, detail="Book not found")

    success = library.delete_book(book_id)

    if not success:
        raise HTTPException(
            status_code=500, detail="The book files are currently in use. Please stop the player and try again."
        )

    return {"status": "success", "message": "Book deleted", "book_id": book_id}
