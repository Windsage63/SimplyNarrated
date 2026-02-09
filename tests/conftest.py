"""
Shared test fixtures for BookTalk test suite.
"""

import os
import json
import pytest
import numpy as np
from datetime import datetime

import src.core.job_manager as jm_module
import src.core.library as lib_module
import src.core.tts_engine as tts_module


# ---------------------------------------------------------------------------
# Filesystem fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with uploads/ and library/ subdirs."""
    uploads = tmp_path / "uploads"
    library = tmp_path / "library"
    uploads.mkdir()
    library.mkdir()
    return tmp_path


@pytest.fixture
def tmp_uploads_dir(tmp_data_dir):
    return tmp_data_dir / "uploads"


@pytest.fixture
def tmp_library_dir(tmp_data_dir):
    return tmp_data_dir / "library"


# ---------------------------------------------------------------------------
# Singleton-safe manager fixtures (reset globals after each test)
# ---------------------------------------------------------------------------


@pytest.fixture
def job_manager(tmp_data_dir):
    """Initialise a JobManager against a temp directory and reset after test."""
    manager = jm_module.init_job_manager(str(tmp_data_dir))
    yield manager
    jm_module._job_manager = None


@pytest.fixture
def library_manager(tmp_library_dir):
    """Initialise a LibraryManager against a temp directory and reset after test."""
    manager = lib_module.init_library_manager(str(tmp_library_dir))
    yield manager
    lib_module._library_manager = None


# ---------------------------------------------------------------------------
# TTS engine fixture (session-scoped to avoid reloading model)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tts_engine():
    """
    Provide the real Kokoro TTS engine, loaded once per session.
    """
    engine = tts_module.get_tts_engine()
    engine.initialize()
    yield engine
    # Don't cleanup — let the process end naturally
    tts_module._tts_engine = None


# ---------------------------------------------------------------------------
# Sample file fixtures
# ---------------------------------------------------------------------------

SAMPLE_TXT_CONTENT = """\
My Test Book

Chapter 1
This is the first chapter of the book. It contains several sentences.
The quick brown fox jumps over the lazy dog. Testing paragraph flow.

This is a second paragraph in chapter one.

Chapter 2
This is the second chapter. It is shorter but still valid.
Another sentence here for good measure.
"""

SAMPLE_MD_CONTENT = """\
# My Markdown Book

## Chapter One

This is **bold** text and *italic* text.
Here is a [link](https://example.com) to somewhere.

## Chapter Two

Some `inline code` and a list:

- Item one
- Item two
"""


@pytest.fixture
def sample_txt_file(tmp_uploads_dir):
    """Write a sample .txt file into the uploads dir and return its path."""
    path = tmp_uploads_dir / "sample.txt"
    path.write_text(SAMPLE_TXT_CONTENT, encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_md_file(tmp_uploads_dir):
    """Write a sample .md file into the uploads dir and return its path."""
    path = tmp_uploads_dir / "sample.md"
    path.write_text(SAMPLE_MD_CONTENT, encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_library_book(tmp_library_dir):
    """
    Pre-populate a book in the library with metadata and a tiny valid WAV file.
    Returns (book_id, book_dir_path).
    """
    book_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    book_dir = tmp_library_dir / book_id
    book_dir.mkdir()

    metadata = {
        "id": book_id,
        "title": "Test Book",
        "author": "Test Author",
        "source_file": "source.txt",
        "original_filename": "my_book.txt",
        "voice": "af_heart",
        "total_chapters": 1,
        "total_duration": "0m",
        "created_at": datetime.now().isoformat(),
        "format": "wav",
        "quality": "sd",
        "chapters": [
            {
                "number": 1,
                "title": "Chapter 1",
                "duration": "0:02",
                "audio_path": "chapter_01.wav",
                "completed": True,
            }
        ],
    }

    with open(book_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)

    # Write a tiny valid WAV via scipy
    from scipy.io import wavfile

    sr = 24000
    duration = 0.5  # half a second
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    wavfile.write(str(book_dir / "chapter_01.wav"), sr, tone)

    return book_id, str(book_dir)


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


@pytest.fixture
async def app_client(tmp_data_dir, tmp_library_dir):
    """
    Async httpx client wired to the FastAPI app with temp directories.
    Resets all singletons after the test.
    """
    import httpx
    from httpx import ASGITransport
    from src.main import app

    # Initialise singletons with temp paths
    jm_module.init_job_manager(str(tmp_data_dir))
    lib_module.init_library_manager(str(tmp_library_dir))

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Teardown
    jm_module._job_manager = None
    lib_module._library_manager = None
    tts_module._tts_engine = None
