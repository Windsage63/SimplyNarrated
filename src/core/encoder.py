"""
@fileoverview BookTalk - Audio Encoder, Convert raw audio to MP3/WAV and manage chapter files
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
import io
import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class EncoderSettings:
    """Audio encoding settings."""

    format: str = "mp3"  # mp3 or wav
    bitrate: str = "192k"  # For MP3: 128k (SD), 192k (HD), 320k (Ultra)
    sample_rate: int = 24000
    channels: int = 1


# Quality presets
QUALITY_PRESETS = {
    "sd": EncoderSettings(bitrate="128k"),
    "hd": EncoderSettings(bitrate="192k"),
    "ultra": EncoderSettings(bitrate="320k"),
}


def get_encoder_settings(quality: str = "hd", format: str = "mp3") -> EncoderSettings:
    """Get encoder settings for a quality preset."""
    preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["hd"])
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

    # For WAV format, try scipy first (no ffmpeg needed)
    if settings.format == "wav":
        try:
            from scipy.io import wavfile

            wavfile.write(output_path, sample_rate, audio_int)
            return output_path
        except ImportError:
            pass  # Fall through to pydub

    # Try pydub (requires ffmpeg for MP3)
    try:
        from pydub import AudioSegment

        # Create AudioSegment from numpy array
        audio_segment = AudioSegment(
            audio_int.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,  # 16-bit
            channels=settings.channels,
        )

        # Export based on format
        if settings.format == "mp3":
            audio_segment.export(
                output_path,
                format="mp3",
                bitrate=settings.bitrate,
            )
        elif settings.format == "wav":
            audio_segment.export(
                output_path,
                format="wav",
            )
        else:
            raise ValueError(f"Unsupported format: {settings.format}")

        return output_path

    except FileNotFoundError as e:
        # ffmpeg not found - fall back to scipy for WAV
        if settings.format == "mp3":
            print("[WARNING] ffmpeg not found. Install ffmpeg for MP3 support.")
            print("[WARNING] Falling back to WAV format...")
            # Change output path to .wav
            output_path = output_path.rsplit(".", 1)[0] + ".wav"
            settings.format = "wav"

        # Use scipy for WAV
        from scipy.io import wavfile

        wavfile.write(output_path, sample_rate, audio_int)
        return output_path


def concatenate_audio_files(
    file_paths: list,
    output_path: str,
    format: str = "mp3",
) -> str:
    """
    Concatenate multiple audio files into one.

    Args:
        file_paths: List of paths to audio files
        output_path: Path for the output file
        format: Output format (mp3 or wav)

    Returns:
        Path to the concatenated file
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        raise ImportError("pydub is required for audio concatenation")

    if not file_paths:
        raise ValueError("No files to concatenate")

    # Load first file
    combined = AudioSegment.from_file(file_paths[0])

    # Append remaining files
    for path in file_paths[1:]:
        audio = AudioSegment.from_file(path)
        combined += audio

    # Export
    combined.export(output_path, format=format)
    return output_path


def get_audio_duration(file_path: str) -> float:
    """Get duration of an audio file in seconds."""
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0  # pydub uses milliseconds
    except Exception:
        return 0.0


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def add_id3_metadata(
    file_path: str,
    title: str,
    track_number: int = 1,
    album: Optional[str] = None,
    artist: Optional[str] = None,
    cover_path: Optional[str] = None,
) -> None:
    """
    Add ID3 metadata to an MP3 file.

    Note: Requires mutagen library for full ID3 support.
    For now, this is a stub that can be implemented later.
    """
    # TODO: Implement ID3 tagging with mutagen
    pass
