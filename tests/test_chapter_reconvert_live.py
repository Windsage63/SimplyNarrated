import asyncio
import json

import pytest
import static_ffmpeg

from src.core.chapter_reconvert import process_chapter_reconvert_job
from src.core.job_manager import init_job_manager
from src.core.tts_engine import init_tts_engine
from tests.conftest import create_library_book


@pytest.mark.live_tts
def test_process_chapter_reconvert_job_generates_real_audio_and_updates_metadata(tmp_path):
    static_ffmpeg.add_paths()

    data_dir = tmp_path / "data"
    library_dir = data_dir / "library"
    library_dir.mkdir(parents=True, exist_ok=True)
    job_manager = init_job_manager(str(data_dir))

    book_id, book_dir, _metadata = create_library_book(
        library_dir,
        chapter_text="This is a live reconvert sample for a single chapter.",
        title="Reconvert Test Book",
        author="Reconvert Author",
    )

    engine = init_tts_engine()
    job = job_manager.create_job("chapter_01_reconvert", str(book_dir / "chapter_01.txt"))

    try:
        asyncio.run(
            process_chapter_reconvert_job(
                job,
                {
                    "book_id": book_id,
                    "chapter_number": 1,
                    "book_dir": str(book_dir),
                    "output_dir": str(book_dir),
                    "model": "kokoro",
                    "narrator_voice": "af_heart",
                },
            )
        )
    finally:
        engine.cleanup()

    audio_path = book_dir / "chapter_01.mp3"
    metadata_path = book_dir / "metadata.json"

    assert audio_path.exists()
    assert audio_path.stat().st_size > 0

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["model"] == "kokoro"
    assert metadata["voice"] == "af_heart"
    assert metadata["quality"] == "sd"
    assert metadata["format"] == "mp3"
    assert metadata["total_duration"] != "0:00"
    assert metadata["chapters"][0]["audio_path"] == "chapter_01.mp3"
    assert metadata["chapters"][0]["text_path"] == "chapter_01.txt"
    assert metadata["chapters"][0]["completed"] is True
    assert metadata["chapters"][0]["duration"] != "0:00"