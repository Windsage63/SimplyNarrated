import asyncio
import json

import numpy as np

from src.core.job_manager import init_job_manager
from src.core.pipeline import process_book
from src.core.text_parser import ParsedTextChapter, ParsedTextDocument


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


def test_process_book_uses_parsed_txt_content_without_speech_renderer(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    job_manager = init_job_manager(str(data_dir))

    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    source_txt = uploads_dir / "input.txt"
    source_txt.write_text("Raw source text", encoding="utf-8")

    job = job_manager.create_job("input.txt", str(source_txt))
    job.output_dir = str(data_dir / "library" / job.id)
    (data_dir / "library" / job.id).mkdir(parents=True, exist_ok=True)

    parsed_document = ParsedTextDocument(
        title="Parsed TXT",
        author="Parser",
        format="txt",
        chapters=[
            ParsedTextChapter(
                number=1,
                title="Chapter 1",
                content="Speech-ready chapter text from the parser.",
            )
        ],
    )
    fake_tts = _FakeTTSEngine()

    def fake_convert_source_document(file_path, output_dir):
        assert file_path.endswith("source.txt")
        assert output_dir == job.output_dir
        return parsed_document

    def fake_encode_audio(_audio, _sample_rate, output_path, _settings):
        with open(output_path, "wb") as handle:
            handle.write(b"mp3")
        return output_path

    def fake_embed_mp3_metadata(file_path, **kwargs):
        return file_path

    async def fake_sleep(_seconds):
        return None

    def fail_render(_chapter):
        raise AssertionError("speech_renderer should not run for parsed TXT chapters")

    monkeypatch.setattr("src.core.pipeline.convert_source_document", fake_convert_source_document)
    monkeypatch.setattr("src.core.pipeline.get_tts_engine", lambda: fake_tts)
    monkeypatch.setattr("src.core.pipeline.render_chapter_text", fail_render)
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
            },
        )
    )

    book_dir = data_dir / "library" / job.id
    assert (book_dir / "source.txt").exists()
    assert (book_dir / "chapter_01.txt").read_text(encoding="utf-8") == "Speech-ready chapter text from the parser."
    metadata = json.loads((book_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["title"] == "Parsed TXT"
    assert metadata["author"] == "Parser"
    assert metadata["source_file"] == "source.txt"
    assert fake_tts.calls == [("Speech-ready chapter text from the parser.", "af_heart", 1.0)]