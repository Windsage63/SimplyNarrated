"""
Tests for the speech renderer.
"""

from src.core.docling_adapter import ImportedChapter, ImportedChunk
from src.core.speech_renderer import (
    estimate_duration_seconds,
    format_total_duration,
    normalize_speech_text,
    render_chapter_text,
)


class TestNormalizeSpeechText:
    def test_strips_markdown_but_preserves_paragraphs(self):
        text = "**Bold** line\n\n- Item one\n- Item two\n\n[Link](https://example.com)"

        normalized = normalize_speech_text(text)

        assert "Bold line" in normalized
        assert "Item one" in normalized
        assert "Item two" in normalized
        assert "Link" in normalized
        assert "https://example.com" not in normalized
        assert "\n\n" in normalized


class TestRenderChapterText:
    def test_renders_title_and_nested_headings(self):
        chapter = ImportedChapter(
            number=1,
            title="Chapter 1",
            chunks=[
                ImportedChunk(
                    text="Opening paragraph.",
                    headings=["Book Title", "Chapter 1"],
                ),
                ImportedChunk(
                    text="Section paragraph.",
                    headings=["Book Title", "Chapter 1", "Section A"],
                ),
            ],
        )

        rendered = render_chapter_text(chapter)

        assert rendered.startswith("Chapter 1")
        assert "Section A" in rendered
        assert "Opening paragraph." in rendered
        assert "Section paragraph." in rendered

    def test_preserves_paragraph_spacing(self):
        chapter = ImportedChapter(
            number=1,
            title="Chapter 1",
            chunks=[
                ImportedChunk(
                    text="First paragraph.\n\nSecond paragraph.",
                    headings=["Chapter 1"],
                )
            ],
        )

        rendered = render_chapter_text(chapter)

        assert "First paragraph.\n\nSecond paragraph." in rendered


class TestDurationHelpers:
    def test_estimated_duration_is_positive(self):
        duration = estimate_duration_seconds("word " * 300, speed=1.0)
        assert duration > 0

    def test_format_total_duration_aggregates_texts(self):
        total = format_total_duration(["word " * 150, "word " * 150], speed=1.0)
        assert total == "2:00"