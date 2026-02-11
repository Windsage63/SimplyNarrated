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
import numpy as np
from typing import Optional
from dataclasses import dataclass


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


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
