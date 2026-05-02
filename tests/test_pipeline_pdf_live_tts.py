import asyncio
import json

import pytest
import static_ffmpeg

from src.core.docling_adapter import ImportedChapter, ImportedChunk, ImportedDocument
from src.core.job_manager import init_job_manager
from src.core.pipeline import process_book
from src.core.tts_engine import init_tts_engine


@pytest.mark.live_tts
def test_process_book_with_live_tts_writes_real_audio(monkeypatch, tmp_path):
    static_ffmpeg.add_paths()

    data_dir = tmp_path / "data"
    job_manager = init_job_manager(str(data_dir))

    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    source_pdf = uploads_dir / "live-input.pdf"
    source_pdf.write_bytes(b"%PDF-1.4 live test")

    job = job_manager.create_job("live-input.pdf", str(source_pdf))
    job.output_dir = str(data_dir / "library" / job.id)
    (data_dir / "library" / job.id).mkdir(parents=True, exist_ok=True)

    imported_document = ImportedDocument(
        title="Live PDF Preservation",
        author="Live Test Author",
        format="pdf",
        chapters=[
            ImportedChapter(
                number=1,
                title="Chapter 1",
                chunks=[ImportedChunk(text="A short live synthesis sample for PDF preservation.", headings=[])],
            )
        ],
        cover_filename=None,
    )

    engine = init_tts_engine()

    def fake_convert_source_document(file_path, output_dir):
        assert file_path.endswith("source.pdf")
        assert output_dir == job.output_dir
        return imported_document

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("src.core.pipeline.convert_source_document", fake_convert_source_document)
    monkeypatch.setattr(
        "src.core.pipeline.render_chapter_text",
        lambda chapter: f"{chapter.title}\n\n{chapter.chunks[0].text}",
    )
    monkeypatch.setattr("src.core.pipeline.asyncio.sleep", fake_sleep)

    try:
        asyncio.run(
            process_book(
                job,
                {
                    "model": "kokoro",
                    "narrator_voice": "af_heart",
                },
            )
        )
    finally:
        engine.cleanup()

    book_dir = data_dir / "library" / job.id
    audio_path = book_dir / "chapter_01.mp3"
    text_path = book_dir / "chapter_01.txt"
    metadata_path = book_dir / "metadata.json"

    assert (book_dir / "source.pdf").exists()
    assert audio_path.exists()
    assert audio_path.stat().st_size > 0
    assert text_path.read_text(encoding="utf-8") == "Chapter 1\n\nA short live synthesis sample for PDF preservation."

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["title"] == "Live PDF Preservation"
    assert metadata["author"] == "Live Test Author"
    assert metadata["model"] == "kokoro"
    assert metadata["cover_url"] is None
    assert metadata["chapters"][0]["audio_path"] == "chapter_01.mp3"
    assert metadata["chapters"][0]["text_path"] == "chapter_01.txt"