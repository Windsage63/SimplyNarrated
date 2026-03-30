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
from typing import Any, Dict, List

import numpy as np
from pydub import AudioSegment

from src.core.chunker import chunk_chapters
from src.core.tts_engine import get_tts_engine
from src.core.encoder import (
    embed_mp3_metadata,
    encode_audio,
    get_encoder_settings,
    format_duration,
)
from src.core.job_manager import Job

logger = logging.getLogger(__name__)


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

    # NOTE: metadata.json is read once at the start and written at the end with no
    # file-level locking. Concurrent writes for different chapters of the same book
    # would cause data loss. This is safe only because JobManager's semaphore
    # (max_concurrent_jobs=1) serialises all jobs. Do not increase concurrency
    # without adding proper file-level locking (e.g. filelock) here.
    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)

    with open(text_path, "r", encoding="utf-8") as chapter_file:
        chapter_text = chapter_file.read().strip()

    if not chapter_text:
        raise RuntimeError("Chapter text is empty")

    voice_id = config.get("narrator_voice") or metadata.get("voice") or "af_heart"
    speed = float(config.get("speed") if config.get("speed") is not None else 1.0)
    quality = config.get("quality") or metadata.get("quality") or "sd"

    requested_format = config.get("format") or metadata.get("format") or "mp3"
    if requested_format != "mp3":
        raise RuntimeError("Only MP3 chapter reconversion is supported")

    encoder_settings = get_encoder_settings(quality=quality, format="mp3")

    job.total_chapters = 1
    job.current_chapter = chapter_number

    job_manager.update_progress(
        job.id,
        10.0,
        chapter_number,
        f"Rebuilding chapter {chapter_number} text chunks...",
    )

    chapter_title = f"Chapter {chapter_number}"
    for chapter_meta in metadata.get("chapters", []):
        if int(chapter_meta.get("number", 0)) == chapter_number:
            chapter_title = chapter_meta.get("title") or chapter_title
            break

    chunks = chunk_chapters([(chapter_title, chapter_text)])

    tts_engine = get_tts_engine()
    if not tts_engine.is_initialized():
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, tts_engine.initialize)

    job_manager.update_progress(
        job.id,
        30.0,
        chapter_number,
        f"Generating audio for chapter {chapter_number}...",
    )

    loop = asyncio.get_running_loop()
    chunk_audio = []
    sample_rate = 24000

    for index, chunk in enumerate(chunks):
        progress = 30.0 + (index / max(1, len(chunks))) * 40.0
        job_manager.update_progress(
            job.id,
            progress,
            chapter_number,
            f"Synthesizing chapter {chapter_number} segment {index + 1}/{len(chunks)}...",
        )

        audio, sample_rate = await loop.run_in_executor(
            None,
            lambda content=chunk.content, voice=voice_id, rate=speed: tts_engine.generate_speech(
                content,
                voice,
                rate,
            ),
        )
        chunk_audio.append(audio)

    merged_audio = np.concatenate(chunk_audio) if len(chunk_audio) > 1 else chunk_audio[0]

    job_manager.update_progress(
        job.id,
        75.0,
        chapter_number,
        f"Encoding chapter {chapter_number} to MP3...",
    )

    await loop.run_in_executor(
        None,
        lambda: encode_audio(merged_audio, sample_rate, temp_audio_path, encoder_settings),
    )

    cover_path = None
    for candidate in ("cover.jpg", "cover.jpeg", "cover.png"):
        candidate_path = os.path.join(book_dir, candidate)
        if os.path.exists(candidate_path):
            cover_path = candidate_path
            break

    await loop.run_in_executor(
        None,
        lambda: embed_mp3_metadata(
            temp_audio_path,
            title=chapter_title,
            album=metadata.get("title"),
            artist=metadata.get("author"),
            track_number=chapter_number,
            total_tracks=len(metadata.get("chapters", [])) or None,
            cover_path=cover_path,
        ),
    )

    job_manager.update_progress(
        job.id,
        90.0,
        chapter_number,
        f"Replacing chapter {chapter_number} audio file...",
    )

    await _replace_with_retry(temp_audio_path, audio_path)

    chapter_audio = AudioSegment.from_file(audio_path)
    chapter_duration = format_duration(chapter_audio.duration_seconds)

    for chapter_meta in metadata.get("chapters", []):
        if int(chapter_meta.get("number", 0)) == chapter_number:
            chapter_meta["duration"] = chapter_duration
            chapter_meta["audio_path"] = f"chapter_{chapter_number:02d}.mp3"
            chapter_meta["text_path"] = f"chapter_{chapter_number:02d}.txt"
            chapter_meta["completed"] = True
            break

    metadata["voice"] = voice_id
    metadata["quality"] = quality
    metadata["format"] = "mp3"
    metadata["total_duration"] = _format_total_duration_from_chapters(metadata.get("chapters", []))

    with open(metadata_path, "w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=2)

    job_manager.update_progress(
        job.id,
        100.0,
        chapter_number,
        f"Chapter {chapter_number} reconversion complete.",
    )

    logger.info("Chapter reconversion complete: book=%s chapter=%s", book_id, chapter_number)
