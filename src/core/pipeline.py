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
import asyncio
from typing import Dict, Any

from src.core.parser import parse_file
from src.core.chunker import chunk_chapters, get_total_duration
from src.core.tts_engine import get_tts_engine
from src.core.encoder import encode_audio, get_encoder_settings, format_duration
from src.core.job_manager import Job


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
        import shutil

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

        # Phase 2: Chunk the text
        job_manager._add_activity(job, "Preparing chapters for audio generation...")
        await asyncio.sleep(0.1)

        chunks = chunk_chapters(document.chapters)
        job.total_chapters = len(chunks)

        total_duration = get_total_duration(chunks)
        job_manager._add_activity(
            job,
            f"Prepared {len(chunks)} audio segments (~{total_duration} estimated)",
            "success",
        )

        # Phase 3: Initialize TTS engine
        job_manager._add_activity(job, "Loading TTS model...")
        await asyncio.sleep(0.1)

        tts_engine = get_tts_engine()
        if not tts_engine.is_initialized():
            # Run initialization in thread pool to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, tts_engine.initialize)

        job_manager._add_activity(job, "TTS model ready", "success")

        # Phase 4: Generate audio for each chunk
        encoder_settings = get_encoder_settings(
            quality=config.get("quality", "sd"),
            format=config.get("format", "mp3"),
        )

        voice_id = config.get("narrator_voice", "af_heart")
        speed = config.get("speed", 1.0)

        for i, chunk in enumerate(chunks):
            # Check for cancellation
            if job.status.value == "cancelled":
                return

            chapter_num = i + 1
            job.current_chapter = chapter_num
            progress = (i / len(chunks)) * 100

            job_manager.update_progress(
                job.id,
                progress,
                chapter_num,
                f"Generating audio for chapter {chapter_num}/{len(chunks)}...",
            )

            # Generate speech (run in thread pool)
            # Use default args to capture values, avoiding lambda closure bug
            loop = asyncio.get_event_loop()
            chunk_content = chunk.content
            audio, sample_rate = await loop.run_in_executor(
                None,
                lambda c=chunk_content, v=voice_id, s=speed: tts_engine.generate_speech(
                    c, v, s
                ),
            )

            # Encode and save
            output_filename = f"chapter_{chapter_num:02d}.{encoder_settings.format}"
            output_path = os.path.join(job.output_dir, output_filename)

            await loop.run_in_executor(
                None,
                lambda a=audio, sr=sample_rate, op=output_path, es=encoder_settings: (
                    encode_audio(a, sr, op, es)
                ),
            )

            job_manager._add_activity(
                job, f"Chapter {chapter_num} complete: {chunk.title}", "success"
            )

            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.1)

        # Phase 5: Finalize
        job_manager._add_activity(job, "Finalizing audiobook...")

        # Build chapter metadata
        chapter_list = []
        for i, chunk in enumerate(chunks):
            chapter_num = i + 1
            chapter_list.append(
                {
                    "number": chapter_num,
                    "title": chunk.title,
                    "duration": format_duration(chunk.estimated_duration)
                    if hasattr(chunk, "estimated_duration")
                    else None,
                    "audio_path": f"chapter_{chapter_num:02d}.{encoder_settings.format}",
                    "completed": True,
                }
            )

        # Save metadata file with full library format
        from datetime import datetime

        metadata = {
            "id": job.id,
            "title": document.title,
            "author": document.author,
            "source_file": os.path.basename(job.file_path),
            "original_filename": job.filename,
            "voice": voice_id,
            "total_chapters": len(chunks),
            "total_duration": total_duration,
            "created_at": datetime.now().isoformat(),
            "format": encoder_settings.format,
            "quality": config.get("quality", "sd"),
            "chapters": chapter_list,
        }

        metadata_path = os.path.join(job.output_dir, "metadata.json")
        import json

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        job.progress = 100.0
        job_manager._add_activity(
            job, f"Audiobook complete! {len(chunks)} chapters generated.", "success"
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        job_manager._add_activity(job, f"Error: {str(e)}", "error")
        raise
