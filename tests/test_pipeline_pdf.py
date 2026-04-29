import asyncio
import json

import numpy as np

from src.core.docling_adapter import ImportedChapter, ImportedChunk, ImportedDocument
from src.core.job_manager import JobStatus, init_job_manager
from src.core.pipeline import process_book


class _FakeTTSEngine:
    def __init__(self):
        self.initialized = False
        self.calls = []

    def is_initialized(self):
        return self.initialized

    def initialize(self):
        self.initialized = True

    def generate_speech(self, text, voice_id, speed):
        self.calls.append((text, voice_id, speed))
        return np.zeros(32, dtype=np.float32), 24000


def test_process_book_preserves_pdf_output_contract(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    job_manager = init_job_manager(str(data_dir))

    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    source_pdf = uploads_dir / "input.pdf"
    source_pdf.write_bytes(b"%PDF-1.4 test")

    job = job_manager.create_job("input.pdf", str(source_pdf))
    job.output_dir = str(data_dir / "library" / job.id)
    (data_dir / "library" / job.id).mkdir(parents=True, exist_ok=True)

    imported_document = ImportedDocument(
        title="Preserved PDF",
        author="Jane PDF",
        format="pdf",
        chapters=[
            ImportedChapter(
                number=1,
                title="Chapter 1",
                chunks=[ImportedChunk(text="Original chunk text [1] (2)", headings=[])],
            )
        ],
        cover_filename="cover.png",
    )
    fake_tts = _FakeTTSEngine()

    def fake_convert_source_document(file_path, output_dir):
        assert file_path.endswith("source.pdf")
        assert output_dir == job.output_dir
        return imported_document

    def fake_encode_audio(_audio, _sample_rate, output_path, _settings):
        with open(output_path, "wb") as handle:
            handle.write(b"mp3")
        return output_path

    embedded = {}

    def fake_embed_mp3_metadata(file_path, **kwargs):
        embedded["file_path"] = file_path
        embedded.update(kwargs)
        return file_path

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("src.core.pipeline.convert_source_document", fake_convert_source_document)
    monkeypatch.setattr("src.core.pipeline.get_tts_engine", lambda: fake_tts)
    monkeypatch.setattr(
        "src.core.pipeline.render_chapter_text",
        lambda chapter: f"{chapter.title}\n\nNarrated text [1] (2)",
    )
    monkeypatch.setattr("src.core.pipeline.encode_audio", fake_encode_audio)
    monkeypatch.setattr("src.core.pipeline.embed_mp3_metadata", fake_embed_mp3_metadata)
    monkeypatch.setattr("src.core.pipeline.asyncio.sleep", fake_sleep)

    asyncio.run(
        process_book(
            job,
            {
                "narrator_voice": "af_heart",
                "speed": 1.0,
                "quality": "sd",
                "remove_square_bracket_numbers": True,
                "remove_paren_numbers": True,
            },
        )
    )

    metadata_path = data_dir / "library" / job.id / "metadata.json"
    chapter_text_path = data_dir / "library" / job.id / "chapter_01.txt"
    audio_path = data_dir / "library" / job.id / "chapter_01.mp3"
    moved_source_path = data_dir / "library" / job.id / "source.pdf"
    expected_chapter_text = "Chapter 1\n\nNarrated text  "

    assert moved_source_path.exists()
    assert audio_path.exists()
    assert chapter_text_path.read_text(encoding="utf-8") == expected_chapter_text

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["title"] == "Preserved PDF"
    assert metadata["author"] == "Jane PDF"
    assert metadata["cover_url"] == f"/api/book/{job.id}/cover"
    assert metadata["source_file"] == "source.pdf"
    assert metadata["total_chapters"] == 1
    assert metadata["chapters"][0]["number"] == 1
    assert metadata["chapters"][0]["audio_path"] == "chapter_01.mp3"
    assert metadata["chapters"][0]["text_path"] == "chapter_01.txt"
    assert embedded["artist"] == "Jane PDF"
    assert embedded["cover_path"].endswith("cover.png")
    assert fake_tts.calls == [(expected_chapter_text, "af_heart", 1.0)]
    assert job.total_chapters == 1
    assert job.status == JobStatus.PENDING