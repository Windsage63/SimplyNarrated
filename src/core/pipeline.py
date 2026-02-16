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
import shutil
import asyncio
import logging
import numpy as np
from typing import Dict, Any
from datetime import datetime

from src.core.parser import parse_file
from src.core.parser import extract_cover_image
from src.core.chunker import chunk_text
from src.core.tts_engine import get_tts_engine
from src.core.encoder import (
    encode_audio,
    get_encoder_settings,
    format_duration,
    mux_m4a_from_segments,
)
from src.core.job_manager import Job, JobStatus

logger = logging.getLogger(__name__)


def _sanitize_book_filename(title: str, fallback: str) -> str:
    candidate = re.sub(r"[\\/:*?\"<>|]+", " ", title or "")
    candidate = re.sub(r"\s+", " ", candidate).strip().strip(".")
    return candidate or fallback


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
            shutil.move(job.file_path, new_source_path)
            job.file_path = new_source_path
            job_manager._add_activity(job, "Source file moved to library", "info")
        except Exception as e:
            job_manager._add_activity(
                job, f"Note: Source file already in place or move failed: {e}", "info"
            )

        # Phase 1: Parse the file
        job_manager._add_activity(job, "Extracting text from file...")
        await asyncio.sleep(0.1)  # Yield to event loop

        document = parse_file(job.file_path)
        job_manager._add_activity(
            job,
            f"Found {len(document.chapters)} chapters in '{document.title}'",
            "success",
        )

        # Phase 1a: Attempt to extract cover image
        cover_filename = extract_cover_image(job.file_path, job.output_dir)
        if cover_filename:
            job_manager._add_activity(job, "Cover image extracted from source file", "success")

        # Phase 1b: Remove footnote/number references if requested
        strip_square = config.get("remove_square_bracket_numbers", False)
        strip_paren = config.get("remove_paren_numbers", False)
        if strip_square or strip_paren:
            cleaned_chapters = []
            for ch_title, ch_content in document.chapters:
                if strip_square:
                    ch_content = re.sub(r"\[\d+\]", "", ch_content)
                if strip_paren:
                    ch_content = re.sub(r"\(\d+\)", "", ch_content)
                cleaned_chapters.append((ch_title, ch_content))
            document.chapters = cleaned_chapters
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

        # Phase 2: Prepare natural chapters for audio generation
        job_manager._add_activity(job, "Preparing chapters for audio generation...")
        await asyncio.sleep(0.1)

        natural_chapters = document.chapters
        job.total_chapters = len(natural_chapters)
        job_manager._add_activity(
            job,
            f"Prepared {len(natural_chapters)} natural chapters",
            "success",
        )

        # Phase 3: Initialize TTS engine
        job_manager._add_activity(job, "Loading TTS model...")
        await asyncio.sleep(0.1)

        tts_engine = get_tts_engine()
        if not tts_engine.is_initialized():
            # Run initialization in thread pool to not block
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, tts_engine.initialize)

        job_manager._add_activity(job, "TTS model ready", "success")

        # Phase 4: Generate audio for each chunk
        encoder_settings = get_encoder_settings(
            quality=config.get("quality", "sd"),
            format="m4a",
        )

        voice_id = config.get("narrator_voice", "af_heart")
        speed = config.get("speed", 1.0)

        segment_dir = os.path.join(job.output_dir, "_segments")
        os.makedirs(segment_dir, exist_ok=True)

        chapter_list = []
        segment_paths = []
        transcript_sections = []
        transcript_cursor = 0
        cumulative_seconds = 0.0

        for i, (chapter_title, chapter_text) in enumerate(natural_chapters):
            # Check for cancellation
            if job.status == JobStatus.CANCELLED:
                return

            chapter_num = i + 1
            job.current_chapter = chapter_num
            progress = (i / len(natural_chapters)) * 100

            job_manager.update_progress(
                job.id,
                progress,
                chapter_num,
                f"Generating audio for chapter {chapter_num}/{len(natural_chapters)}...",
            )

            parts = chunk_text(chapter_text, chapter_title=chapter_title)
            chapter_audio_parts = []
            chapter_sample_rate = None

            loop = asyncio.get_running_loop()

            for part in parts:
                audio, sample_rate = await loop.run_in_executor(
                    None,
                    lambda c=part.content, v=voice_id, s=speed: tts_engine.generate_speech(
                        c, v, s
                    ),
                )

                if chapter_sample_rate is None:
                    chapter_sample_rate = sample_rate
                elif chapter_sample_rate != sample_rate:
                    raise RuntimeError("Inconsistent sample rates returned by TTS engine")

                chapter_audio_parts.append(audio)

            if not chapter_audio_parts or chapter_sample_rate is None:
                raise RuntimeError(f"No audio generated for chapter {chapter_num}")

            chapter_audio = (
                chapter_audio_parts[0]
                if len(chapter_audio_parts) == 1
                else np.concatenate(chapter_audio_parts)
            )
            chapter_duration_seconds = len(chapter_audio) / float(chapter_sample_rate)

            segment_filename = f"segment_{chapter_num:03d}.m4a"
            segment_path = os.path.join(segment_dir, segment_filename)

            await loop.run_in_executor(
                None,
                lambda a=chapter_audio, sr=chapter_sample_rate, op=segment_path, es=encoder_settings: (
                    encode_audio(a, sr, op, es)
                ),
            )
            segment_paths.append(segment_path)

            section_text = f"{chapter_title}\n\n{chapter_text.strip()}"
            if transcript_sections:
                transcript_cursor += 2
            transcript_start = transcript_cursor
            transcript_sections.append(section_text)
            transcript_cursor += len(section_text)
            transcript_end = transcript_cursor

            chapter_start = cumulative_seconds
            chapter_end = cumulative_seconds + chapter_duration_seconds
            cumulative_seconds = chapter_end

            chapter_list.append(
                {
                    "number": chapter_num,
                    "title": chapter_title,
                    "duration": format_duration(chapter_duration_seconds),
                    "start_seconds": round(chapter_start, 3),
                    "end_seconds": round(chapter_end, 3),
                    "transcript_start": transcript_start,
                    "transcript_end": transcript_end,
                    "completed": True,
                }
            )

            job_manager._add_activity(
                job, f"Chapter {chapter_num} complete: {chapter_title}", "success"
            )

            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.1)

        # Phase 5: Finalize
        job_manager._add_activity(job, "Finalizing audiobook...")

        book_base_name = _sanitize_book_filename(document.title, job.id)
        book_filename = f"{book_base_name}.m4a"
        book_output_path = os.path.join(job.output_dir, book_filename)

        cover_path = None
        if cover_filename:
            cover_path = os.path.join(job.output_dir, cover_filename)

        created_at = datetime.now().isoformat()

        await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: mux_m4a_from_segments(
                segment_paths=segment_paths,
                output_path=book_output_path,
                title=document.title,
                author=document.author,
                chapters=chapter_list,
                cover_path=cover_path,
                bitrate=encoder_settings.bitrate,
                custom_metadata={
                    "SIMPLYNARRATED_ID": job.id,
                    "SIMPLYNARRATED_CREATED_AT": created_at,
                    "SIMPLYNARRATED_ORIGINAL_FILENAME": job.filename,
                    "SIMPLYNARRATED_TRANSCRIPT_PATH": "transcript.txt",
                    "SIMPLYNARRATED_VOICE": voice_id,
                    "SIMPLYNARRATED_QUALITY": config.get("quality", "sd"),
                },
            ),
        )

        transcript_content = "\n\n".join(transcript_sections)
        transcript_filename = "transcript.txt"
        transcript_path = os.path.join(job.output_dir, transcript_filename)
        with open(transcript_path, "w", encoding="utf-8") as tf:
            tf.write(transcript_content)

        shutil.rmtree(segment_dir, ignore_errors=True)

        total_duration = format_duration(cumulative_seconds)

        job.progress = 100.0
        job_manager._add_activity(
            job,
            f"Audiobook complete! {len(chapter_list)} chapters embedded in {book_filename}.",
            "success",
        )

    except Exception as e:
        logger.exception("Pipeline error for job %s", job.id)
        job_manager._add_activity(job, f"Error: {str(e)}", "error")
        raise
