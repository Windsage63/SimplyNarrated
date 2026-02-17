"""
Shared pytest fixtures for metadata editing tests.
"""

import os
import shutil
import uuid
import pytest


# ---------------------------------------------------------------------------
# Helpers to create a tiny valid M4A file without requiring the TTS engine
# ---------------------------------------------------------------------------


def _make_silent_m4a(path: str) -> str:
    """Create a ~1-second silent M4A file using pydub + ffmpeg."""
    from pydub import AudioSegment

    silence = AudioSegment.silent(duration=1000, frame_rate=24000)
    silence = silence.set_channels(1)
    silence.export(path, format="ipod", codec="aac", bitrate="96k")
    return path


def _stamp_metadata(m4a_path: str) -> str:
    """Write initial metadata + chapters via the existing ffmpeg path."""
    from src.core.encoder import update_m4a_metadata

    book_id = str(uuid.uuid4())
    chapters = [
        {
            "number": 1,
            "title": "Introduction",
            "start_seconds": 0.0,
            "end_seconds": 0.5,
            "transcript_start": 0,
            "transcript_end": 100,
        },
        {
            "number": 2,
            "title": "Conclusion",
            "start_seconds": 0.5,
            "end_seconds": 1.0,
            "transcript_start": 100,
            "transcript_end": 200,
        },
    ]

    update_m4a_metadata(
        file_path=m4a_path,
        title="Original Title",
        author="Original Author",
        chapters=chapters,
        custom_metadata={
            "SIMPLYNARRATED_ID": book_id,
            "SIMPLYNARRATED_CREATED_AT": "2026-01-15T12:00:00",
            "SIMPLYNARRATED_ORIGINAL_FILENAME": "test_book.txt",
            "SIMPLYNARRATED_TRANSCRIPT_PATH": "transcript.txt",
        },
    )
    return m4a_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def small_m4a(tmp_path_factory):
    """Session-scoped: create once, copy per test via small_m4a_copy."""
    base = tmp_path_factory.mktemp("audio")
    path = str(base / "fixture.m4a")
    _make_silent_m4a(path)
    _stamp_metadata(path)
    return path


@pytest.fixture
def small_m4a_copy(small_m4a, tmp_path):
    """Function-scoped isolated copy of the fixture M4A."""
    dest = str(tmp_path / "audiobook.m4a")
    shutil.copy2(small_m4a, dest)
    return dest


@pytest.fixture
def sample_cover(tmp_path):
    """Create a minimal valid JPEG file for cover art testing."""
    # Use pydub's AudioSegment trick is not applicable here.
    # Instead, create a tiny but valid JPEG using raw bytes.
    # Minimal JFIF: SOI + APP0 + DQT + SOF0 + DHT + SOS + EOI
    import struct
    import io

    cover_path = str(tmp_path / "cover.jpg")

    # Simplest approach: use a 1x1 PPM and convert with ffmpeg
    ppm_path = str(tmp_path / "cover.ppm")
    with open(ppm_path, "wb") as f:
        f.write(b"P6\n1 1\n255\n")
        f.write(b"\xff\x00\x00")  # red pixel

    import subprocess

    subprocess.run(
        ["ffmpeg", "-y", "-i", ppm_path, cover_path],
        capture_output=True,
    )

    if not os.path.exists(cover_path):
        # Fallback: write raw JFIF markers that mutagen can accept
        with open(cover_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 20 + b"\xff\xd9")

    return cover_path
