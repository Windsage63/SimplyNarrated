"""
@fileoverview SimplyNarrated - Processing Pipeline, Orchestrates the full conversion from file to audiobook
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
import json
import shutil
import asyncio
import logging
from functools import partial
from typing import Dict, Any
from datetime import datetime

import aiofiles

from src.core.document_router import convert_source_document
from src.core.speech_renderer import (
    estimate_duration_seconds,
    format_total_duration,
    render_chapter_text,
)
from src.core.text_parser import ParsedTextChapter
from src.core.tts_engine import get_tts_engine
from src.core.encoder import (
    embed_mp3_metadata,
    encode_audio,
    get_encoder_settings,
    format_duration,
)
from src.core.job_manager import Job, JobStatus

logger = logging.getLogger(__name__)


async def _run_blocking(function, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(function, *args, **kwargs))


async def _write_text_file(path: str, content: str) -> None:
    async with aiofiles.open(path, "w", encoding="utf-8") as handle:
        await handle.write(content)


async def _write_json_file(path: str, payload: Dict[str, Any]) -> None:
    async with aiofiles.open(path, "w", encoding="utf-8") as handle:
        await handle.write(json.dumps(payload, indent=2))


async def process_book(job: Job, config: Dict[str, Any]) -> None:
    """
    Main processing pipeline for converting a book to audiobook.

    This function is called by the JobManager as a background task.

    Args:
        job: The job object with file path and state
        config: Processing configuration (voice, speed, quality, format)
    """
    from src.core.job_manager import get_job_manager

    job_manager = get_job_manager()

    try:
        # Move source file from uploads to book's library directory
        source_ext = os.path.splitext(job.file_path)[1]
        new_source_path = os.path.join(job.output_dir, f"source{source_ext}")

        try:
            await _run_blocking(shutil.move, job.file_path, new_source_path)
            job.file_path = new_source_path
            job_manager._add_activity(job, "Source file moved to library", "info")
        except Exception as e:
            job_manager._add_activity(
                job, f"Note: Source file already in place or move failed: {e}", "info"
            )

        voice_id = config.get("narrator_voice", "af_heart")
        speed = config.get("speed", 1.0)

        # Phase 1: Convert the file
        job_manager._add_activity(job, "Importing source document...")
        await asyncio.sleep(0.1)  # Yield to event loop

        document = await _run_blocking(convert_source_document, job.file_path, job.output_dir)
        job_manager._add_activity(
            job,
            f"Found {len(document.chapters)} chapters in '{document.title}'",
            "success",
        )

        cover_filename = document.cover_filename
        cover_path = os.path.join(job.output_dir, cover_filename) if cover_filename else None
        if cover_filename:
            job_manager._add_activity(job, "Cover image extracted from source file", "success")

        # Phase 1a: Render final speech text and apply optional cleanup
        strip_square = config.get("remove_square_bracket_numbers", False)
        strip_paren = config.get("remove_paren_numbers", False)

        rendered_chapters = []
        for chapter in document.chapters:
            if isinstance(chapter, ParsedTextChapter):
                chapter_text = chapter.content
            else:
                chapter_text = render_chapter_text(chapter)
            if strip_square:
                chapter_text = re.sub(r"\[\d+\]", "", chapter_text)
            if strip_paren:
                chapter_text = re.sub(r"\(\d+\)", "", chapter_text)

            if chapter_text.strip():
                rendered_chapters.append(
                    {
                        "title": chapter.title,
                        "content": chapter_text,
                        "estimated_duration": estimate_duration_seconds(chapter_text, speed=speed),
                    }
                )

        if not rendered_chapters:
            raise RuntimeError("No speech-ready chapters were produced from the source file")

        if strip_square or strip_paren:
            removed = []
            if strip_square:
                removed.append("[N]")
            if strip_paren:
                removed.append("(N)")
            job_manager._add_activity(
                job,
                f"Removed {' and '.join(removed)} footnote references from text",
                "success",
            )

        # Phase 2: Prepare rendered chapters for audio generation
        job_manager._add_activity(job, "Preparing chapters for audio generation...")
        await asyncio.sleep(0.1)

        job.total_chapters = len(rendered_chapters)

        total_duration = format_total_duration(
            [chapter["content"] for chapter in rendered_chapters],
            speed=speed,
        )
        job_manager._add_activity(
            job,
            f"Prepared {len(rendered_chapters)} audio segments (~{total_duration} estimated)",
            "success",
        )

        # Phase 3: Initialize TTS engine
        job_manager._add_activity(job, "Loading TTS model...")
        await asyncio.sleep(0.1)

        tts_engine = get_tts_engine()
        if not tts_engine.is_initialized():
            # Run initialization in thread pool to not block
            await _run_blocking(tts_engine.initialize)

        job_manager._add_activity(job, "TTS model ready", "success")

        # Phase 4: Generate audio for each chunk
        encoder_settings = get_encoder_settings(
            quality=config.get("quality", "sd"),
        )

        for i, chapter in enumerate(rendered_chapters):
            # Check for cancellation
            if job.status == JobStatus.CANCELLED:
                return

            chapter_num = i + 1
            job.current_chapter = chapter_num
            progress = (i / len(rendered_chapters)) * 100

            job_manager.update_progress(
                job.id,
                progress,
                chapter_num,
                f"Generating audio for chapter {chapter_num}/{len(rendered_chapters)}...",
            )

            # Generate speech (run in thread pool)
            # Use default args to capture values, avoiding lambda closure bug
            chapter_content = chapter["content"]
            audio, sample_rate = await _run_blocking(
                tts_engine.generate_speech,
                chapter_content,
                voice_id,
                speed,
            )

            # Encode and save
            output_filename = f"chapter_{chapter_num:02d}.mp3"
            output_path = os.path.join(job.output_dir, output_filename)

            await _run_blocking(encode_audio, audio, sample_rate, output_path, encoder_settings)

            await _run_blocking(
                embed_mp3_metadata,
                output_path,
                title=chapter["title"],
                album=document.title,
                artist=document.author,
                track_number=chapter_num,
                total_tracks=len(rendered_chapters),
                cover_path=cover_path,
            )

            # Save chapter text
            text_filename = f"chapter_{chapter_num:02d}.txt"
            text_path = os.path.join(job.output_dir, text_filename)
            await _write_text_file(text_path, chapter_content)

            job_manager._add_activity(
                job, f"Chapter {chapter_num} complete: {chapter['title']}", "success"
            )

            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.1)

        # Phase 5: Finalize
        job_manager._add_activity(job, "Finalizing audiobook...")

        # Build chapter metadata
        chapter_list = []
        for i, chapter in enumerate(rendered_chapters):
            chapter_num = i + 1
            chapter_list.append(
                {
                    "number": chapter_num,
                    "title": chapter["title"],
                    "duration": format_duration(chapter["estimated_duration"]),
                    "audio_path": f"chapter_{chapter_num:02d}.mp3",
                    "text_path": f"chapter_{chapter_num:02d}.txt",
                    "completed": True,
                }
            )

        # Save metadata file with full library format
        metadata = {
            "id": job.id,
            "title": document.title,
            "author": document.author,
            "cover_url": f"/api/book/{job.id}/cover" if cover_filename else None,
            "source_file": os.path.basename(job.file_path),
            "original_filename": job.filename,
            "voice": voice_id,
            "total_chapters": len(rendered_chapters),
            "total_duration": total_duration,
            "created_at": datetime.now().isoformat(),
            "format": "mp3",
            "quality": config.get("quality", "sd"),
            "chapters": chapter_list,
        }

        metadata_path = os.path.join(job.output_dir, "metadata.json")
        await _write_json_file(metadata_path, metadata)

        job.progress = 100.0
        job_manager._add_activity(
            job, f"Audiobook complete! {len(rendered_chapters)} chapters generated.", "success"
        )

    except Exception as e:
        logger.exception("Pipeline error for job %s", job.id)
        job_manager._add_activity(job, f"Error: {str(e)}", "error")
        raise
