"""
Tests for the audio encoder module.
"""

import base64
import os
import shutil
import pytest
import numpy as np
from mutagen.id3 import ID3

from src.core.encoder import (
    EncoderSettings,
    QUALITY_PRESETS,
    _configure_ffmpeg_paths,
    embed_mp3_metadata,
    get_encoder_settings,
    encode_audio,
    format_duration,
)


# ---------------------------------------------------------------------------
# Helper: generate a short sine-wave array
# ---------------------------------------------------------------------------

def _sine_wave(duration: float = 0.5, sample_rate: int = 24000) -> np.ndarray:
    """Return a float32 sine-wave array."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return (np.sin(2 * np.pi * 440 * t)).astype(np.float32)


# ---------------------------------------------------------------------------
# get_encoder_settings
# ---------------------------------------------------------------------------


class TestGetEncoderSettings:
    def test_sd(self):
        s = get_encoder_settings(quality="sd")
        assert s.bitrate == "128k"

    def test_hd(self):
        s = get_encoder_settings(quality="hd")
        assert s.bitrate == "192k"

    def test_ultra(self):
        s = get_encoder_settings(quality="ultra")
        assert s.bitrate == "320k"

    def test_default_is_sd(self):
        s = get_encoder_settings()
        assert s.bitrate == "128k"

    def test_format_override(self):
        s = get_encoder_settings(quality="sd", format="mp3")
        assert s.format == "mp3"

    def test_unknown_quality_falls_back(self):
        s = get_encoder_settings(quality="invalid")
        assert s.bitrate == "128k"  # falls back to sd


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------


class TestFormatDuration:
    def test_seconds_only(self):
        assert format_duration(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert format_duration(125) == "2:05"

    def test_with_hours(self):
        assert format_duration(3661) == "1:01:01"

    def test_zero(self):
        assert format_duration(0) == "0:00"


# ---------------------------------------------------------------------------
# encode_audio — MP3 (requires ffmpeg via pydub)
# ---------------------------------------------------------------------------


class TestEncodeAudioMp3:
    @staticmethod
    def _ffmpeg_available() -> bool:
        """Check if ffmpeg is available."""
        try:
            _configure_ffmpeg_paths()
            return shutil.which("ffmpeg") is not None
        except ImportError:
            return False

    @pytest.fixture(autouse=True)
    def _skip_if_no_ffmpeg(self):
        if not self._ffmpeg_available():
            pytest.skip("ffmpeg not available")

    def test_creates_mp3_file(self, tmp_path):
        audio = _sine_wave()
        out = str(tmp_path / "test.mp3")
        result = encode_audio(audio, 24000, out, EncoderSettings(format="mp3", bitrate="128k"))
        assert os.path.exists(result)
        assert result.endswith(".mp3")
        assert os.path.getsize(result) > 0

    def test_creates_directory_if_missing(self, tmp_path):
        audio = _sine_wave()
        nested = tmp_path / "a" / "b" / "output.mp3"
        result = encode_audio(audio, 24000, str(nested), EncoderSettings(format="mp3", bitrate="128k"))
        assert os.path.exists(result)

    def test_float32_normalization(self, tmp_path):
        """Float32 input should be normalised to int16 internally."""
        audio = _sine_wave().astype(np.float32)
        out = str(tmp_path / "float.mp3")
        result = encode_audio(audio, 24000, out, EncoderSettings(format="mp3", bitrate="128k"))
        assert os.path.exists(result)

    def test_float64_input(self, tmp_path):
        audio = _sine_wave().astype(np.float64)
        out = str(tmp_path / "f64.mp3")
        result = encode_audio(audio, 24000, out, EncoderSettings(format="mp3", bitrate="128k"))
        assert os.path.exists(result)

    def test_int16_passthrough(self, tmp_path):
        audio = (_sine_wave() * 32767).astype(np.int16)
        out = str(tmp_path / "i16.mp3")
        result = encode_audio(audio, 24000, out, EncoderSettings(format="mp3", bitrate="128k"))
        assert os.path.exists(result)

    def test_mp3_is_readable(self, tmp_path):
        """Verify the output MP3 can be read back by pydub."""
        from pydub import AudioSegment

        audio = _sine_wave(duration=1.0)
        out = str(tmp_path / "readable.mp3")
        encode_audio(audio, 24000, out, EncoderSettings(format="mp3", bitrate="128k"))

        segment = AudioSegment.from_mp3(out)
        assert len(segment) > 0  # duration in ms

    def test_embed_mp3_metadata_without_cover(self, tmp_path):
        audio = _sine_wave(duration=1.0)
        out = str(tmp_path / "tagged.mp3")

        encode_audio(audio, 24000, out, EncoderSettings(format="mp3", bitrate="128k"))
        embed_mp3_metadata(
            out,
            title="Chapter 1",
            album="Example Book",
            artist="Example Author",
            track_number=1,
            total_tracks=3,
        )

        tags = ID3(out)
        assert tags.get("TIT2").text == ["Chapter 1"]
        assert tags.get("TALB").text == ["Example Book"]
        assert tags.get("TPE1").text == ["Example Author"]
        assert tags.get("TRCK").text == ["1/3"]
        assert tags.getall("APIC") == []

    def test_embed_mp3_metadata_with_cover(self, tmp_path):
        audio = _sine_wave(duration=1.0)
        out = str(tmp_path / "cover-tagged.mp3")
        cover_path = tmp_path / "cover.png"

        cover_path.write_bytes(
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wn4xWkAAAAASUVORK5CYII="
            )
        )

        encode_audio(audio, 24000, out, EncoderSettings(format="mp3", bitrate="128k"))
        embed_mp3_metadata(
            out,
            title="Chapter 2",
            album="Example Book",
            artist="Example Author",
            track_number=2,
            total_tracks=3,
            cover_path=str(cover_path),
        )

        tags = ID3(out)
        artwork = tags.getall("APIC")
        assert len(artwork) == 1
        assert artwork[0].mime == "image/png"
        assert artwork[0].data == cover_path.read_bytes()
