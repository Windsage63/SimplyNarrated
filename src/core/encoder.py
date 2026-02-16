"""
@fileoverview SimplyNarrated - Audio Encoder, Convert raw audio to MP3/WAV and manage chapter files
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
import time
import subprocess
import tempfile
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class EncoderSettings:
    """Audio encoding settings."""

    format: str = "m4a"
    bitrate: str = "192k"  # 128k (SD), 192k (HD), 320k (Ultra)
    sample_rate: int = 24000
    channels: int = 1


# Quality presets
QUALITY_PRESETS = {
    "sd": EncoderSettings(bitrate="128k"),
    "hd": EncoderSettings(bitrate="192k"),
    "ultra": EncoderSettings(bitrate="320k"),
}


def get_encoder_settings(quality: str = "sd", format: str = "m4a") -> EncoderSettings:
    """Get encoder settings for a quality preset."""
    preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["sd"])
    return EncoderSettings(
        format=format,
        bitrate=preset.bitrate,
        sample_rate=preset.sample_rate,
        channels=preset.channels,
    )


def encode_audio(
    audio: np.ndarray,
    sample_rate: int,
    output_path: str,
    settings: Optional[EncoderSettings] = None,
) -> str:
    """
    Encode audio array to file.

    Args:
        audio: NumPy array of audio samples
        sample_rate: Sample rate of the audio
        output_path: Path to save the encoded file
        settings: Encoder settings

    Returns:
        Path to the saved file
    """
    if settings is None:
        settings = EncoderSettings()

    # Normalize audio to int16 range
    if audio.dtype == np.float32 or audio.dtype == np.float64:
        audio_int = (audio * 32767).astype(np.int16)
    else:
        audio_int = audio.astype(np.int16)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    from pydub import AudioSegment

    audio_segment = AudioSegment(
        audio_int.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,  # 16-bit
        channels=settings.channels,
    )

    export_format = settings.format.lower()
    export_kwargs = {"bitrate": settings.bitrate}

    if export_format in {"m4a", "m4b"}:
        export_format = "ipod"
        export_kwargs["codec"] = "aac"

    audio_segment.export(output_path, format=export_format, **export_kwargs)

    # Verify the file was written successfully
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(
            f"Audio encoding failed: output file is empty at {output_path}"
        )

    return output_path


def _ffmpeg_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace("=", "\\=")
        .replace("\n", "\\n")
    )


def _write_ffmetadata(
    metadata_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: Optional[List[Dict[str, Any]]] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    lines = [";FFMETADATA1"]
    if title:
        lines.append(f"title={_ffmpeg_escape(title)}")
        lines.append(f"album={_ffmpeg_escape(title)}")
    if author:
        lines.append(f"artist={_ffmpeg_escape(author)}")
        lines.append(f"album_artist={_ffmpeg_escape(author)}")

    custom_payload = {
        str(key): value for key, value in (custom_metadata or {}).items() if value is not None
    }
    if custom_payload:
        lines.append(
            f"comment={_ffmpeg_escape('SNMETA:' + json.dumps(custom_payload, separators=(',', ':')))}"
        )

    if chapters:
        lines.append("track=1/1")

    for chapter in chapters or []:
        start_seconds = float(chapter.get("start_seconds", 0.0) or 0.0)
        end_seconds = float(chapter.get("end_seconds", start_seconds) or start_seconds)
        start_ms = max(0, int(start_seconds * 1000))
        end_ms = max(start_ms + 1, int(end_seconds * 1000))
        chapter_number = int(chapter.get("number", 0) or 0)
        chapter_title = chapter.get("title") or f"Chapter {chapter_number}"
        numbered_title = (
            f"{chapter_number:02d} - {chapter_title}" if chapter_number > 0 else chapter_title
        )

        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start_ms}",
                f"END={end_ms}",
                f"title={_ffmpeg_escape(numbered_title)}",
                f"simplynarrated_chapter={chapter_number or 0}",
                f"simplynarrated_transcript_start={int(chapter.get('transcript_start', 0) or 0)}",
                f"simplynarrated_transcript_end={int(chapter.get('transcript_end', 0) or 0)}",
            ]
        )

    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _run_ffmpeg(command: List[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )


def _run_ffprobe(command: List[str]) -> Dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return json.loads(result.stdout or "{}")


def _replace_with_retries(source_path: str, target_path: str, retries: int = 5, delay: float = 0.25) -> None:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            os.replace(source_path, target_path)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    if last_error:
        raise last_error


def _normalize_tags(raw_tags: Optional[Dict[str, Any]]) -> Dict[str, str]:
    tags: Dict[str, str] = {}
    for key, value in (raw_tags or {}).items():
        if value is None:
            continue
        tags[str(key).lower()] = str(value)
    return tags


def read_m4a_metadata(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    data = _run_ffprobe(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_chapters",
            file_path,
        ]
    )

    fmt = data.get("format", {})
    tags = _normalize_tags(fmt.get("tags"))
    custom_payload: Dict[str, Any] = {}
    comment = tags.get("comment") or ""
    if comment.startswith("SNMETA:"):
        try:
            custom_payload = json.loads(comment[len("SNMETA:") :])
        except Exception:
            custom_payload = {}

    custom_tags = {str(key).lower(): value for key, value in custom_payload.items()}
    duration_seconds = float(fmt.get("duration", 0.0) or 0.0)
    title = tags.get("title") or os.path.splitext(os.path.basename(file_path))[0]
    author = tags.get("artist") or tags.get("album_artist") or None

    chapters: List[Dict[str, Any]] = []
    for idx, chapter in enumerate(data.get("chapters", []), start=1):
        chapter_tags = _normalize_tags(chapter.get("tags"))
        chapter_title = chapter_tags.get("title") or f"Chapter {idx}"
        if " - " in chapter_title and chapter_title.split(" - ", 1)[0].isdigit():
            chapter_title = chapter_title.split(" - ", 1)[1]
        start_seconds = float(chapter.get("start_time", 0.0) or 0.0)
        end_seconds = float(chapter.get("end_time", start_seconds) or start_seconds)
        transcript_start = int(chapter_tags.get("simplynarrated_transcript_start", 0) or 0)
        transcript_end = int(chapter_tags.get("simplynarrated_transcript_end", 0) or 0)
        chapter_number = int(chapter_tags.get("simplynarrated_chapter", idx) or idx)
        chapters.append(
            {
                "number": chapter_number,
                "title": chapter_title,
                "duration": format_duration(max(0.0, end_seconds - start_seconds)),
                "start_seconds": round(start_seconds, 3),
                "end_seconds": round(end_seconds, 3),
                "transcript_start": transcript_start,
                "transcript_end": transcript_end,
                "completed": True,
            }
        )

    return {
        "title": title,
        "author": author,
        "album": tags.get("album") or title,
        "duration_seconds": duration_seconds,
        "total_duration": format_duration(duration_seconds),
        "created_at": custom_tags.get("simplynarrated_created_at"),
        "original_filename": custom_tags.get("simplynarrated_original_filename"),
        "transcript_path": custom_tags.get("simplynarrated_transcript_path") or "transcript.txt",
        "id": custom_tags.get("simplynarrated_id"),
        "voice": custom_tags.get("simplynarrated_voice"),
        "quality": custom_tags.get("simplynarrated_quality"),
        "chapters": chapters,
    }


def mux_m4a_from_segments(
    segment_paths: List[str],
    output_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: List[Dict[str, Any]],
    cover_path: Optional[str] = None,
    bitrate: str = "192k",
    custom_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    if not segment_paths:
        raise ValueError("No audio segments provided for m4a muxing")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        concat_list_path = os.path.join(temp_dir, "concat.txt")
        metadata_path = os.path.join(temp_dir, "metadata.txt")

        with open(concat_list_path, "w", encoding="utf-8") as f:
            for path in segment_paths:
                normalized = os.path.abspath(path).replace("\\", "/")
                normalized = normalized.replace("'", "'\\''")
                f.write(f"file '{normalized}'\n")

        _write_ffmetadata(metadata_path, title, author, chapters, custom_metadata)

        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-f",
            "ffmetadata",
            "-i",
            metadata_path,
        ]

        if cover_path and os.path.exists(cover_path):
            command.extend(
                [
                    "-i",
                    cover_path,
                    "-map",
                    "2:v",
                    "-c:v",
                    "mjpeg",
                    "-disposition:v:0",
                    "attached_pic",
                ]
            )

        command.extend(
            [
                "-map",
                "0:a",
                "-map_metadata",
                "1",
                "-map_chapters",
                "1",
                "-c:a",
                "aac",
                "-b:a",
                bitrate,
                "-movflags",
                "+faststart",
            ]
        )

        command.append(output_path)
        _run_ffmpeg(command)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"M4A muxing failed: output file is empty at {output_path}")

    return output_path


def update_m4a_metadata(
    file_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: Optional[List[Dict[str, Any]]] = None,
    cover_path: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    replace_retries: int = 5,
    retry_delay_seconds: float = 0.25,
) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    output_tmp = f"{file_path}.tmp.m4a"
    if os.path.exists(output_tmp):
        os.remove(output_tmp)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = os.path.join(temp_dir, "metadata.txt")
            _write_ffmetadata(metadata_path, title, author, chapters, custom_metadata)

            command = [
                "ffmpeg",
                "-y",
                "-i",
                file_path,
                "-f",
                "ffmetadata",
                "-i",
                metadata_path,
            ]

            if cover_path and os.path.exists(cover_path):
                command.extend(
                    [
                        "-i",
                        cover_path,
                        "-map",
                        "2:v",
                        "-c:v",
                        "mjpeg",
                        "-disposition:v:0",
                        "attached_pic",
                    ]
                )

            command.extend(
                [
                    "-map",
                    "0:a",
                    "-map_metadata",
                    "1",
                    "-map_chapters",
                    "1",
                    "-c:a",
                    "copy",
                ]
            )

            command.append(output_tmp)
            _run_ffmpeg(command)

        _replace_with_retries(
            source_path=output_tmp,
            target_path=file_path,
            retries=replace_retries,
            delay=retry_delay_seconds,
        )
    except Exception:
        if os.path.exists(output_tmp):
            try:
                os.remove(output_tmp)
            except OSError:
                pass
        raise

    return file_path


def mux_m4b_from_segments(
    segment_paths: List[str],
    output_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: List[Dict[str, Any]],
    cover_path: Optional[str] = None,
    bitrate: str = "192k",
    custom_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    return mux_m4a_from_segments(
        segment_paths=segment_paths,
        output_path=output_path,
        title=title,
        author=author,
        chapters=chapters,
        cover_path=cover_path,
        bitrate=bitrate,
        custom_metadata=custom_metadata,
    )


def update_m4b_metadata(
    file_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: Optional[List[Dict[str, Any]]] = None,
    cover_path: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    replace_retries: int = 5,
    retry_delay_seconds: float = 0.25,
) -> str:
    return update_m4a_metadata(
        file_path=file_path,
        title=title,
        author=author,
        chapters=chapters,
        cover_path=cover_path,
        custom_metadata=custom_metadata,
        replace_retries=replace_retries,
        retry_delay_seconds=retry_delay_seconds,
    )


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
