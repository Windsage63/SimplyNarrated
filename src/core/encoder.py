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

import logging
import os
import numpy as np
from typing import Optional
from dataclasses import dataclass

from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK


logger = logging.getLogger(__name__)


def _configure_ffmpeg_paths() -> None:
    """Add bundled ffmpeg binaries to PATH when available."""
    try:
        import static_ffmpeg

        static_ffmpeg.add_paths()
    except ImportError:
        pass


@dataclass
class EncoderSettings:
    """Audio encoding settings."""

    format: str = "mp3"
    bitrate: str = "192k"  # 128k (SD), 192k (HD), 320k (Ultra)
    sample_rate: int = 24000
    channels: int = 1


# Quality presets
QUALITY_PRESETS = {
    "sd": EncoderSettings(bitrate="128k"),
    "hd": EncoderSettings(bitrate="192k"),
    "ultra": EncoderSettings(bitrate="320k"),
}


def get_encoder_settings(quality: str = "sd", format: str = "mp3") -> EncoderSettings:
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

    _configure_ffmpeg_paths()

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

    audio_segment.export(
        output_path,
        format="mp3",
        bitrate=settings.bitrate,
    )

    # Verify the file was written successfully
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"MP3 encoding failed: output file is empty at {output_path}")

    return output_path


def embed_mp3_metadata(
    file_path: str,
    *,
    title: str,
    album: Optional[str] = None,
    artist: Optional[str] = None,
    track_number: Optional[int] = None,
    total_tracks: Optional[int] = None,
    cover_path: Optional[str] = None,
) -> str:
    """Embed ID3 metadata into an existing MP3 file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot tag missing MP3 file: {file_path}")

    try:
        tags = ID3(file_path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.delall("TIT2")
    tags.delall("TALB")
    tags.delall("TPE1")
    tags.delall("TRCK")
    tags.delall("APIC")

    tags.add(TIT2(encoding=3, text=title))

    if album:
        tags.add(TALB(encoding=3, text=album))

    if artist:
        tags.add(TPE1(encoding=3, text=artist))

    if track_number is not None:
        track_text = str(track_number)
        if total_tracks is not None:
            track_text = f"{track_number}/{total_tracks}"
        tags.add(TRCK(encoding=3, text=track_text))

    if cover_path and os.path.exists(cover_path):
        ext = os.path.splitext(cover_path)[1].lower()
        mime_type = "image/png" if ext == ".png" else "image/jpeg"
        with open(cover_path, "rb") as cover_file:
            tags.add(
                APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc="Cover",
                    data=cover_file.read(),
                )
            )

    tags.save(file_path, v2_version=3)
    return file_path


def _find_cover_path(book_dir: str) -> Optional[str]:
    """Return the current cover file path for a book directory, if any."""
    for candidate in ("cover.jpg", "cover.jpeg", "cover.png"):
        candidate_path = os.path.join(book_dir, candidate)
        if os.path.exists(candidate_path):
            return candidate_path
    return None


def retag_book_mp3_files(book_dir: str, metadata: dict) -> None:
    """Reapply current metadata and cover art to existing chapter MP3 files."""
    chapters = metadata.get("chapters", [])
    total_tracks = len(chapters) or None
    cover_path = _find_cover_path(book_dir)

    for chapter in chapters:
        chapter_number = int(chapter.get("number", 0))
        if chapter_number < 1:
            continue

        audio_name = chapter.get("audio_path") or f"chapter_{chapter_number:02d}.mp3"
        audio_path = os.path.join(book_dir, os.path.basename(audio_name))
        if not audio_path.lower().endswith(".mp3") or not os.path.exists(audio_path):
            continue

        chapter_title = chapter.get("title") or f"Chapter {chapter_number}"
        embed_mp3_metadata(
            audio_path,
            title=chapter_title,
            album=metadata.get("title"),
            artist=metadata.get("author"),
            track_number=chapter_number,
            total_tracks=total_tracks,
            cover_path=cover_path,
        )

        logger.info("Retagged MP3 metadata for chapter %s", chapter_number)


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
