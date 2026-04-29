import asyncio
import json

import pytest
import static_ffmpeg

from src.core.job_manager import init_job_manager
from src.core.pipeline import process_book
from src.core.tts_engine import init_tts_engine


@pytest.mark.live_tts
def test_process_book_with_live_txt_parser_writes_audio_and_parser_artifacts(monkeypatch, tmp_path):
    static_ffmpeg.add_paths()

    data_dir = tmp_path / "data"
    job_manager = init_job_manager(str(data_dir))

    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    source_txt = uploads_dir / "live-input.txt"
    source_txt.write_text(
        "Live TXT Book\n\nBy Live Author\n\nCHAPTER 1\n\nThis is a short live synthesis sample for the TXT parser path.\nIt should be reflowed into a single paragraph before narration.\n",
        encoding="utf-8",
    )

    job = job_manager.create_job("live-input.txt", str(source_txt))
    job.output_dir = str(data_dir / "library" / job.id)
    (data_dir / "library" / job.id).mkdir(parents=True, exist_ok=True)

    engine = init_tts_engine()

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("src.core.pipeline.asyncio.sleep", fake_sleep)

    try:
        asyncio.run(
            process_book(
                job,
                {
                    "narrator_voice": "af_heart",
                    "speed": 1.0,
                    "quality": "sd",
                },
            )
        )
    finally:
        engine.cleanup()

    book_dir = data_dir / "library" / job.id
    source_path = book_dir / "source.txt"
    cleaned_path = book_dir / "source.cleaned.txt"
    report_path = book_dir / "parse-report.json"
    text_path = book_dir / "chapter_01.txt"
    audio_path = book_dir / "chapter_01.mp3"
    metadata_path = book_dir / "metadata.json"

    assert source_path.exists()
    assert cleaned_path.exists()
    assert report_path.exists()
    assert text_path.exists()
    assert audio_path.exists()
    assert audio_path.stat().st_size > 0

    cleaned_text = cleaned_path.read_text(encoding="utf-8")
    assert cleaned_text.startswith("Live TXT Book")
    assert "By Live Author" in cleaned_text
    assert "CHAPTER 1" in cleaned_text
    assert "It should be reflowed into a single paragraph before narration." in cleaned_text

    chapter_text = text_path.read_text(encoding="utf-8")
    assert chapter_text == (
        "This is a short live synthesis sample for the TXT parser path. "
        "It should be reflowed into a single paragraph before narration."
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["title"] == "Live TXT Book"
    assert report["title_source"] == "first_block"
    assert report["author"] == "Live Author"
    assert report["chapter_count"] == 1
    assert report["chapter_titles"] == ["CHAPTER 1"]
    assert report["explicit_chapter_markers"] == 1
    assert report["fallback_split_used"] is False

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["title"] == "Live TXT Book"
    assert metadata["author"] == "Live Author"
    assert metadata["source_file"] == "source.txt"
    assert metadata["cover_url"] is None
    assert metadata["chapters"][0]["title"] == "CHAPTER 1"
    assert metadata["chapters"][0]["audio_path"] == "chapter_01.mp3"
    assert metadata["chapters"][0]["text_path"] == "chapter_01.txt"