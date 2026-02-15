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
) -> None:
    lines = [";FFMETADATA1"]
    if title:
        lines.append(f"title={_ffmpeg_escape(title)}")
    if author:
        lines.append(f"artist={_ffmpeg_escape(author)}")

    for chapter in chapters or []:
        start_seconds = float(chapter.get("start_seconds", 0.0) or 0.0)
        end_seconds = float(chapter.get("end_seconds", start_seconds) or start_seconds)
        start_ms = max(0, int(start_seconds * 1000))
        end_ms = max(start_ms + 1, int(end_seconds * 1000))
        chapter_title = chapter.get("title") or f"Chapter {chapter.get('number', 0)}"

        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start_ms}",
                f"END={end_ms}",
                f"title={_ffmpeg_escape(chapter_title)}",
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


def mux_m4b_from_segments(
    segment_paths: List[str],
    output_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: List[Dict[str, Any]],
    cover_path: Optional[str] = None,
    bitrate: str = "192k",
) -> str:
    if not segment_paths:
        raise ValueError("No audio segments provided for m4b muxing")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        concat_list_path = os.path.join(temp_dir, "concat.txt")
        metadata_path = os.path.join(temp_dir, "metadata.txt")

        with open(concat_list_path, "w", encoding="utf-8") as f:
            for path in segment_paths:
                normalized = os.path.abspath(path).replace("\\", "/")
                normalized = normalized.replace("'", "'\\''")
                f.write(f"file '{normalized}'\n")

        _write_ffmetadata(metadata_path, title, author, chapters)

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
        raise RuntimeError(f"M4B muxing failed: output file is empty at {output_path}")

    return output_path


def update_m4b_metadata(
    file_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: Optional[List[Dict[str, Any]]] = None,
    cover_path: Optional[str] = None,
) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    output_tmp = f"{file_path}.tmp.m4a"
    if os.path.exists(output_tmp):
        os.remove(output_tmp)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = os.path.join(temp_dir, "metadata.txt")
            _write_ffmetadata(metadata_path, title, author, chapters)

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
                    "-c:a",
                    "copy",
                ]
            )

            command.append(output_tmp)
            _run_ffmpeg(command)

        os.replace(output_tmp, file_path)
    except Exception:
        if os.path.exists(output_tmp):
            try:
                os.remove(output_tmp)
            except OSError:
                pass
        raise

    return file_path


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
