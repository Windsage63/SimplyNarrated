"""
Unit tests for src/core/chapter_reconvert.py helpers and reconvert flow.
"""

import asyncio
import json
import os

import numpy as np
import pytest

from src.core.chapter_reconvert import (
    _parse_duration_to_seconds,
    _format_total_duration_from_chapters,
    _replace_with_retry,
    process_chapter_reconvert_job,
)


# ---------------------------------------------------------------------------
# _parse_duration_to_seconds
# ---------------------------------------------------------------------------


class TestParseDurationToSeconds:
    def test_mm_ss(self):
        assert _parse_duration_to_seconds("1:30") == 90.0

    def test_hh_mm_ss(self):
        assert _parse_duration_to_seconds("1:02:03") == 3723.0

    def test_empty(self):
        assert _parse_duration_to_seconds("") == 0.0

    def test_none_like(self):
        assert _parse_duration_to_seconds(None) == 0.0

    def test_invalid(self):
        assert _parse_duration_to_seconds("not-a-time") == 0.0

    def test_zero(self):
        assert _parse_duration_to_seconds("0:00") == 0.0


# ---------------------------------------------------------------------------
# _format_total_duration_from_chapters
# ---------------------------------------------------------------------------


class TestFormatTotalDurationFromChapters:
    def test_sums_durations(self):
        chapters = [
            {"duration": "1:00"},
            {"duration": "2:30"},
        ]
        result = _format_total_duration_from_chapters(chapters)
        # 60 + 150 = 210 seconds = 3:30
        assert result == "3:30"

    def test_empty_list(self):
        result = _format_total_duration_from_chapters([])
        assert result == "0:00"

    def test_missing_duration_key(self):
        chapters = [{"title": "Chapter 1"}]
        result = _format_total_duration_from_chapters(chapters)
        assert result == "0:00"


# ---------------------------------------------------------------------------
# _replace_with_retry (async)
# ---------------------------------------------------------------------------


class TestReplaceWithRetry:
    async def test_successful_replace(self, tmp_path):
        src = tmp_path / "source.tmp"
        dst = tmp_path / "destination.mp3"
        src.write_bytes(b"audio data")

        await _replace_with_retry(str(src), str(dst))

        assert dst.exists()
        assert not src.exists()
        assert dst.read_bytes() == b"audio data"

    async def test_raises_when_source_missing(self, tmp_path):
        src = tmp_path / "missing.tmp"
        dst = tmp_path / "destination.mp3"

        with pytest.raises((FileNotFoundError, RuntimeError)):
            await _replace_with_retry(str(src), str(dst), retries=1)


class TestProcessChapterReconvertJob:
    async def test_uses_saved_text_exactly(self, tmp_path, job_manager, monkeypatch):
        import src.core.chapter_reconvert as chapter_reconvert_module

        book_dir = tmp_path / "book"
        book_dir.mkdir()

        metadata = {
            "id": "book-id",
            "title": "Book Title",
            "author": "Author Name",
            "voice": "af_heart",
            "quality": "sd",
            "format": "mp3",
            "chapters": [
                {
                    "number": 1,
                    "title": "Chapter 1",
                    "duration": "0:05",
                    "audio_path": "chapter_01.mp3",
                    "text_path": "chapter_01.txt",
                    "completed": True,
                }
            ],
        }
        metadata_path = book_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        saved_text = "Chapter 1\n\nParagraph one.\n\nParagraph two with [12] markers.\n"
        text_path = book_dir / "chapter_01.txt"
        text_path.write_text(saved_text, encoding="utf-8")

        captured = {}

        class FakeEngine:
            def is_initialized(self):
                return True

            def generate_speech(self, text, voice_id, speed):
                captured["text"] = text
                captured["voice_id"] = voice_id
                captured["speed"] = speed
                return np.zeros(24000, dtype=np.float32), 24000

        class FakeAudioSegment:
            duration_seconds = 1.0

        def fake_encode_audio(audio, sample_rate, output_path, settings):
            with open(output_path, "wb") as audio_file:
                audio_file.write(b"fake-mp3")
            return output_path

        monkeypatch.setattr(chapter_reconvert_module, "get_tts_engine", lambda: FakeEngine())
        monkeypatch.setattr(chapter_reconvert_module, "encode_audio", fake_encode_audio)
        monkeypatch.setattr(chapter_reconvert_module, "embed_mp3_metadata", lambda *args, **kwargs: args[0])
        monkeypatch.setattr(chapter_reconvert_module.AudioSegment, "from_file", lambda _: FakeAudioSegment())

        job = job_manager.create_job("chapter_reconvert", str(text_path))
        job.output_dir = str(book_dir)

        await process_chapter_reconvert_job(
            job,
            {
                "book_id": "book-id",
                "chapter_number": 1,
                "book_dir": str(book_dir),
                "output_dir": str(book_dir),
                "narrator_voice": "af_heart",
                "speed": 1.0,
                "quality": "sd",
                "format": "mp3",
            },
        )

        assert captured["text"] == saved_text
        assert captured["voice_id"] == "af_heart"
        assert captured["speed"] == 1.0

        updated_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert updated_metadata["chapters"][0]["audio_path"] == "chapter_01.mp3"
        assert updated_metadata["chapters"][0]["text_path"] == "chapter_01.txt"
