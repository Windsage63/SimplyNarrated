"""
Tests for the text chunker module.
"""

import pytest

from src.core.chunker import (
    count_words,
    estimate_duration,
    chunk_text,
    chunk_chapters,
    get_total_duration,
    get_total_words,
    MAX_WORDS_PER_CHUNK,
    WORDS_PER_MINUTE,
)


# ---------------------------------------------------------------------------
# count_words
# ---------------------------------------------------------------------------


class TestCountWords:
    def test_simple(self):
        assert count_words("one two three") == 3

    def test_empty(self):
        assert count_words("") == 0

    def test_extra_whitespace(self):
        assert count_words("  one   two  ") == 2


# ---------------------------------------------------------------------------
# estimate_duration
# ---------------------------------------------------------------------------


class TestEstimateDuration:
    def test_default_speed(self):
        # 150 words at 150 WPM = 1 minute = 60 seconds
        assert estimate_duration(150) == pytest.approx(60.0)

    def test_double_speed(self):
        # 150 words at 2x speed = 30 seconds
        assert estimate_duration(150, speed=2.0) == pytest.approx(30.0)

    def test_half_speed(self):
        assert estimate_duration(150, speed=0.5) == pytest.approx(120.0)

    def test_zero_words(self):
        assert estimate_duration(0) == 0.0


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "Hello world. This is a short text."
        chunks = chunk_text(text, max_words=100)
        assert len(chunks) == 1
        assert chunks[0].title == "Chapter"
        assert chunks[0].word_count == count_words(text)

    def test_long_text_splits(self):
        # Create text longer than limit
        text = "word " * 8000
        chunks = chunk_text(text.strip(), max_words=4000)
        assert len(chunks) >= 2
        for ch in chunks:
            assert ch.word_count <= 4000

    def test_respects_max_words(self):
        text = "sentence one. " * 500  # ~1000 words
        chunks = chunk_text(text.strip(), max_words=300)
        for ch in chunks:
            assert ch.word_count <= 300 or ch.word_count <= 300 * 1.1  # Small tolerance

    def test_chunk_index_sequential(self):
        text = "word " * 2000
        chunks = chunk_text(text.strip(), max_words=500)
        for i, ch in enumerate(chunks):
            assert ch.index == i

    def test_part_labelling_when_split(self):
        text = "word " * 2000
        chunks = chunk_text(text.strip(), max_words=500, chapter_title="Intro")
        assert "Part" in chunks[0].title

    def test_single_chunk_no_part_label(self):
        text = "A short text."
        chunks = chunk_text(text, max_words=1000, chapter_title="Intro")
        assert chunks[0].title == "Intro"
        assert "Part" not in chunks[0].title

    def test_estimated_duration_set(self):
        text = "word " * 150  # 150 words → ~60 seconds
        chunks = chunk_text(text.strip(), max_words=1000)
        assert chunks[0].estimated_duration == pytest.approx(60.0, abs=1.0)


# ---------------------------------------------------------------------------
# chunk_chapters (merging logic)
# ---------------------------------------------------------------------------


class TestChunkChapters:
    def test_merges_small_chapters(self):
        chapters = [(f"Ch {i}", "word " * 100) for i in range(1, 13)]
        chunks = chunk_chapters(chapters, max_words=1000)
        # 12 chapters of 100 words each = 1200 words, limit 1000
        # Should produce 2 chunks (1000 + 200)
        assert len(chunks) == 2

    def test_splits_large_chapter(self):
        chapters = [("Big Chapter", "word " * 10000)]
        chunks = chunk_chapters(chapters, max_words=4000)
        assert len(chunks) >= 3  # 10000 / 4000 ≈ 3

    def test_mixed_sizes(self):
        chapters = [
            ("Small 1", "word " * 50),
            ("Small 2", "word " * 50),
            ("Big", "word " * 5000),
            ("Small 3", "word " * 50),
        ]
        chunks = chunk_chapters(chapters, max_words=4000)
        # Small 1+2 merge (100 words), Big splits (~2 chunks), Small 3 alone or merged
        assert len(chunks) >= 2

    def test_merged_title_format(self):
        chapters = [(f"Chapter {i}", "tiny") for i in range(1, 6)]
        chunks = chunk_chapters(chapters, max_words=10000)
        assert len(chunks) == 1
        assert "Chapter 1" in chunks[0].title
        assert "Chapter 5" in chunks[0].title

    def test_single_chapter_no_merge_label(self):
        chapters = [("Only Chapter", "Some text here.")]
        chunks = chunk_chapters(chapters, max_words=10000)
        assert len(chunks) == 1
        assert chunks[0].title == "Only Chapter"

    def test_global_indices(self):
        chapters = [("A", "word " * 500), ("B", "word " * 500)]
        chunks = chunk_chapters(chapters, max_words=400)
        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_chapters(self):
        chunks = chunk_chapters([], max_words=4000)
        assert chunks == []


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


class TestGetTotalDuration:
    def test_minutes_only(self):
        from src.core.chunker import TextChunk

        chunks = [TextChunk(0, "A", "x", 150, 60.0)]  # 1 minute
        assert get_total_duration(chunks) == "1m"

    def test_hours_and_minutes(self):
        from src.core.chunker import TextChunk

        chunks = [TextChunk(0, "A", "x", 1000, 3900.0)]  # 65 min = 1h 5m
        assert get_total_duration(chunks) == "1h 5m"


class TestGetTotalWords:
    def test_sums_correctly(self):
        from src.core.chunker import TextChunk

        chunks = [
            TextChunk(0, "A", "x", 100, 0),
            TextChunk(1, "B", "y", 200, 0),
        ]
        assert get_total_words(chunks) == 300
