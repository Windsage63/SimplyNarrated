"""
@fileoverview SimplyNarrated - Chapter reconversion pipeline for single-chapter audio regeneration
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
import json
import asyncio
import logging
from functools import partial
from typing import Any, Dict, List

import aiofiles
from pydub import AudioSegment

from src.core.tts_engine import get_tts_engine
from src.core.encoder import (
    embed_mp3_metadata,
    encode_audio,
    get_encoder_settings,
    format_duration,
)
from src.core.job_manager import Job
from src.core.metadata_store import update_metadata_file
from src.models.schemas import JobStatus

logger = logging.getLogger(__name__)


async def _run_blocking(function, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(function, *args, **kwargs))


async def _read_json_file(path: str) -> Dict[str, Any]:
    async with aiofiles.open(path, "r", encoding="utf-8") as handle:
        return json.loads(await handle.read())


async def _read_text_file(path: str) -> str:
    async with aiofiles.open(path, "r", encoding="utf-8") as handle:
        return await handle.read()


async def _remove_file_if_exists(path: str) -> None:
    if os.path.exists(path):
        await _run_blocking(os.remove, path)


def _parse_duration_to_seconds(value: str) -> float:
    parts = [p.strip() for p in (value or "").split(":") if p.strip()]
    if not parts:
        return 0.0
    try:
        if len(parts) == 2:
            minutes, seconds = parts
            return (int(minutes) * 60) + int(seconds)
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return (int(hours) * 3600) + (int(minutes) * 60) + int(seconds)
    except ValueError:
        return 0.0
    return 0.0


def _format_total_duration_from_chapters(chapters: List[Dict[str, Any]]) -> str:
    total_seconds = 0.0
    for chapter in chapters:
        total_seconds += _parse_duration_to_seconds(chapter.get("duration", ""))
    return format_duration(total_seconds)


def _apply_reconvert_metadata_update(
    metadata: Dict[str, Any],
    *,
    chapter_number: int,
    chapter_duration: str,
    voice_id: str,
    quality: str,
) -> None:
    chapter_found = False
    for chapter_meta in metadata.get("chapters", []):
        if int(chapter_meta.get("number", 0)) == chapter_number:
            chapter_meta["duration"] = chapter_duration
            chapter_meta["audio_path"] = f"chapter_{chapter_number:02d}.mp3"
            chapter_meta["text_path"] = f"chapter_{chapter_number:02d}.txt"
            chapter_meta["completed"] = True
            chapter_found = True
            break

    if not chapter_found:
        raise RuntimeError(f"Chapter {chapter_number} metadata not found")

    metadata["voice"] = voice_id
    metadata["quality"] = quality
    metadata["format"] = "mp3"
    metadata["total_duration"] = _format_total_duration_from_chapters(metadata.get("chapters", []))


async def _replace_with_retry(source_path: str, destination_path: str, retries: int = 6) -> None:
    retry_delay_seconds = 0.5
    last_error = None

    for _ in range(retries):
        try:
            await _run_blocking(os.replace, source_path, destination_path)
            return
        except (PermissionError, OSError) as error:
            last_error = error
            await asyncio.sleep(retry_delay_seconds)

    if os.path.exists(source_path):
        try:
            await _run_blocking(os.remove, source_path)
        except OSError:
            pass

    raise RuntimeError(
        "Unable to update chapter audio because the file is in use. "
        "Stop playback for this chapter and try again."
    ) from last_error


async def process_chapter_reconvert_job(job: Job, config: Dict[str, Any]) -> None:
    """Regenerate audio for a single chapter using edited chapter text."""
    from src.core.job_manager import get_job_manager

    job_manager = get_job_manager()

    book_id = config["book_id"]
    chapter_number = int(config["chapter_number"])
    book_dir = config["book_dir"]

    metadata_path = os.path.join(book_dir, "metadata.json")
    text_path = os.path.join(book_dir, f"chapter_{chapter_number:02d}.txt")
    audio_path = os.path.join(book_dir, f"chapter_{chapter_number:02d}.mp3")
    temp_audio_path = os.path.join(book_dir, f"chapter_{chapter_number:02d}.{job.id}.tmp.mp3")

    if not os.path.exists(metadata_path):
        raise RuntimeError("Book metadata not found")
    if not os.path.exists(text_path):
        raise RuntimeError("Chapter text not found")

    metadata = await _read_json_file(metadata_path)

    chapter_text = await _read_text_file(text_path)

    if not chapter_text.strip():
        raise RuntimeError("Chapter text is empty")

    voice_id = config.get("narrator_voice") or metadata.get("voice") or "af_heart"
    speed = float(config.get("speed") if config.get("speed") is not None else 1.0)
    quality = config.get("quality") or metadata.get("quality") or "sd"

    requested_format = config.get("format") or metadata.get("format") or "mp3"
    if requested_format != "mp3":
        raise RuntimeError("Only MP3 chapter reconversion is supported")

    encoder_settings = get_encoder_settings(quality=quality)

    job.total_chapters = 1
    job.current_chapter = chapter_number

    job_manager.update_progress(
        job.id,
        10.0,
        chapter_number,
        f"Preparing saved text for chapter {chapter_number}...",
    )

    chapter_title = f"Chapter {chapter_number}"
    for chapter_meta in metadata.get("chapters", []):
        if int(chapter_meta.get("number", 0)) == chapter_number:
            chapter_title = chapter_meta.get("title") or chapter_title
            break

    tts_engine = get_tts_engine()
    if not tts_engine.is_initialized():
        await _run_blocking(tts_engine.initialize)

    job_manager.update_progress(
        job.id,
        30.0,
        chapter_number,
        f"Generating audio for chapter {chapter_number}...",
    )

    audio, sample_rate = await _run_blocking(
        tts_engine.generate_speech,
        chapter_text,
        voice_id,
        speed,
    )

    if job.status == JobStatus.CANCELLED:
        await _remove_file_if_exists(temp_audio_path)
        return

    job_manager.update_progress(
        job.id,
        75.0,
        chapter_number,
        f"Encoding chapter {chapter_number} to MP3...",
    )

    await _run_blocking(encode_audio, audio, sample_rate, temp_audio_path, encoder_settings)

    if job.status == JobStatus.CANCELLED:
        await _remove_file_if_exists(temp_audio_path)
        return

    cover_path = None
    for candidate in ("cover.jpg", "cover.jpeg", "cover.png"):
        candidate_path = os.path.join(book_dir, candidate)
        if os.path.exists(candidate_path):
            cover_path = candidate_path
            break

    await _run_blocking(
        embed_mp3_metadata,
        temp_audio_path,
        title=chapter_title,
        album=metadata.get("title"),
        artist=metadata.get("author"),
        track_number=chapter_number,
        total_tracks=len(metadata.get("chapters", [])) or None,
        cover_path=cover_path,
    )

    if job.status == JobStatus.CANCELLED:
        await _remove_file_if_exists(temp_audio_path)
        return

    job_manager.update_progress(
        job.id,
        90.0,
        chapter_number,
        f"Replacing chapter {chapter_number} audio file...",
    )

    await _replace_with_retry(temp_audio_path, audio_path)

    chapter_duration_seconds = await _run_blocking(
        lambda: AudioSegment.from_file(audio_path).duration_seconds
    )
    chapter_duration = format_duration(chapter_duration_seconds)

    await _run_blocking(
        update_metadata_file,
        metadata_path,
        partial(
            _apply_reconvert_metadata_update,
            chapter_number=chapter_number,
            chapter_duration=chapter_duration,
            voice_id=voice_id,
            quality=quality,
        ),
    )

    job_manager.update_progress(
        job.id,
        100.0,
        chapter_number,
        f"Chapter {chapter_number} reconversion complete.",
    )

    logger.info("Chapter reconversion complete: book=%s chapter=%s", book_id, chapter_number)
