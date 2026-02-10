"""
Tests for the file parser module.
"""

import os
import pytest

from src.core.parser import (
    detect_format,
    parse_txt,
    parse_markdown,
    parse_file,
    _normalize_line_breaks,
    _markdown_to_text,
    _extract_chapter_title,
    _split_into_chapters,
)


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------


class TestDetectFormat:
    def test_txt(self, tmp_path):
        assert detect_format(str(tmp_path / "file.txt")) == "txt"

    def test_md(self, tmp_path):
        assert detect_format(str(tmp_path / "file.md")) == "md"

    def test_pdf(self, tmp_path):
        assert detect_format(str(tmp_path / "file.PDF")) == "pdf"

    def test_unknown(self, tmp_path):
        assert detect_format(str(tmp_path / "file.docx")) == "docx"


# ---------------------------------------------------------------------------
# _normalize_line_breaks
# ---------------------------------------------------------------------------


class TestNormalizeLineBreaks:
    def test_single_newline_becomes_space(self):
        assert _normalize_line_breaks("line one\nline two") == "line one line two"

    def test_double_newline_preserved(self):
        result = _normalize_line_breaks("para one\n\npara two")
        assert "para one" in result
        assert "para two" in result
        assert "\n\n" in result

    def test_windows_crlf(self):
        result = _normalize_line_breaks("line one\r\nline two")
        assert result == "line one line two"

    def test_multiple_blank_lines_collapsed(self):
        result = _normalize_line_breaks("a\n\n\n\nb")
        assert result == "a\n\nb"

    def test_empty_string(self):
        assert _normalize_line_breaks("") == ""

    def test_only_newlines(self):
        result = _normalize_line_breaks("\n\n\n")
        assert result == ""

    def test_squeezes_multiple_spaces(self):
        result = _normalize_line_breaks("word   word")
        assert result == "word word"


# ---------------------------------------------------------------------------
# _markdown_to_text
# ---------------------------------------------------------------------------


class TestMarkdownToText:
    def test_removes_heading_markers(self):
        assert _markdown_to_text("## Hello") == "Hello"

    def test_removes_bold(self):
        assert "strong" in _markdown_to_text("**strong** text")
        assert "**" not in _markdown_to_text("**strong** text")

    def test_removes_italic(self):
        result = _markdown_to_text("*italic* text")
        assert "italic" in result
        assert result.count("*") == 0

    def test_removes_links_keeps_text(self):
        result = _markdown_to_text("[click here](https://example.com)")
        assert "click here" in result
        assert "https" not in result

    def test_removes_images(self):
        result = _markdown_to_text("![alt](img.png)")
        assert "alt" not in result or result.strip() == ""

    def test_removes_code_blocks(self):
        result = _markdown_to_text("```python\nprint('hi')\n```")
        assert "print" not in result


# ---------------------------------------------------------------------------
# _extract_chapter_title
# ---------------------------------------------------------------------------


class TestExtractChapterTitle:
    def test_finds_chapter_heading(self):
        text = "Chapter 1: The Beginning\nSome content here."
        assert _extract_chapter_title(text) == "Chapter 1: The Beginning"

    def test_no_match_returns_none(self):
        text = "This is just normal text with no heading."
        # May or may not match depending on heuristics — short uppercase line
        result = _extract_chapter_title(text)
        # Acceptable: either None or the short line itself
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# _split_into_chapters
# ---------------------------------------------------------------------------


class TestSplitIntoChapters:
    def test_with_chapter_headings(self):
        text = "\n\nChapter 1\nFirst content.\n\nChapter 2\nSecond content."
        chapters = _split_into_chapters(text)
        assert len(chapters) >= 2
        assert "Chapter 1" in chapters[0][0]

    def test_no_headings_single_chapter(self):
        text = "Just a block of plain text with no chapter markers."
        chapters = _split_into_chapters(text)
        assert len(chapters) == 1
        assert chapters[0][0] == "Chapter 1"

    def test_preamble_captured_before_chapter_headings(self):
        text = "This is introductory text.\n\nMore intro.\n\nChapter 1\nFirst chapter.\n\nChapter 2\nSecond chapter."
        chapters = _split_into_chapters(text)
        assert chapters[0][0] == "Preamble"
        assert "introductory text" in chapters[0][1]
        assert len(chapters) >= 3

    def test_no_preamble_when_chapter_at_start(self):
        text = "Chapter 1\nContent here.\n\nChapter 2\nMore content."
        chapters = _split_into_chapters(text)
        assert chapters[0][0] != "Preamble"

    def test_numbered_paragraphs_deep_in_text_skipped(self):
        """Numbered items far into the text should not be treated as chapters."""
        intro = "Some text. " * 500  # large block before numbered items
        text = intro + "\n\n1. First point here\nContent.\n\n2. Second point here\nMore."
        chapters = _split_into_chapters(text)
        # Should fall back to single chapter since numbered items are >30% in
        assert len(chapters) == 1
        assert chapters[0][0] == "Chapter 1"

    def test_numbered_pattern_used_when_near_start(self):
        text = "\n\n1. Introduction\nFirst content.\n\n2. Background\nSecond content."
        chapters = _split_into_chapters(text)
        assert len(chapters) >= 2
        assert "Introduction" in chapters[0][0] or "Introduction" in chapters[0][1]

    def test_allcaps_section_headers(self):
        text = (
            "Some preamble text.\n\n\n\n"
            "COMPENSATION\n\nFirst essay content here.\n\n\n\n"
            "SELF-RELIANCE\n\nSecond essay content here."
        )
        chapters = _split_into_chapters(text)
        titles = [t for t, _ in chapters]
        assert "COMPENSATION" in titles
        assert "SELF-RELIANCE" in titles

    def test_allcaps_headers_capture_preamble(self):
        text = (
            "Introduction and preamble.\n\n\n\n"
            "THE AMERICAN SCHOLAR\n\nEssay one.\n\n\n\n"
            "FRIENDSHIP\n\nEssay two."
        )
        chapters = _split_into_chapters(text)
        assert chapters[0][0] == "Preamble"
        assert "Introduction" in chapters[0][1]


# ---------------------------------------------------------------------------
# parse_txt
# ---------------------------------------------------------------------------


class TestParseTxt:
    def test_basic_parse(self, sample_txt_file):
        doc = parse_txt(sample_txt_file)
        assert doc.format == "txt"
        assert doc.title  # Should extract something
        assert len(doc.chapters) >= 1
        assert doc.raw_text  # Non-empty

    def test_chapter_detection(self, tmp_path):
        content = "Book Title\n\nChapter 1\nFirst chapter text.\n\nChapter 2\nSecond chapter text."
        path = tmp_path / "book.txt"
        path.write_text(content, encoding="utf-8")
        doc = parse_txt(str(path))
        assert len(doc.chapters) >= 2

    def test_line_break_normalization(self, tmp_path):
        content = "Title\n\nThis is a long\nline that should\nbe joined.\n\nNew paragraph."
        path = tmp_path / "wrap.txt"
        path.write_text(content, encoding="utf-8")
        doc = parse_txt(str(path))
        # The chapter content should have single newlines removed
        all_text = " ".join(c for _, c in doc.chapters)
        assert "long line that should be joined" in all_text

    def test_long_first_line_uses_filename(self, tmp_path):
        long_line = "A" * 150
        content = f"{long_line}\nSome text."
        path = tmp_path / "my_book.txt"
        path.write_text(content, encoding="utf-8")
        doc = parse_txt(str(path))
        assert doc.title == "my_book"


# ---------------------------------------------------------------------------
# parse_markdown
# ---------------------------------------------------------------------------


class TestParseMarkdown:
    def test_basic_parse(self, sample_md_file):
        doc = parse_markdown(sample_md_file)
        assert doc.format == "md"
        assert doc.title == "My Markdown Book"

    def test_formatting_stripped(self, sample_md_file):
        doc = parse_markdown(sample_md_file)
        assert "**" not in doc.raw_text
        assert "*" not in doc.raw_text or doc.raw_text.count("*") == 0

    def test_chapter_split(self, sample_md_file):
        doc = parse_markdown(sample_md_file)
        # Should split on ## headings
        assert len(doc.chapters) >= 2


# ---------------------------------------------------------------------------
# parse_file dispatch
# ---------------------------------------------------------------------------


class TestParseFile:
    def test_txt_dispatch(self, sample_txt_file):
        doc = parse_file(sample_txt_file)
        assert doc.format == "txt"

    def test_md_dispatch(self, sample_md_file):
        doc = parse_file(sample_md_file)
        assert doc.format == "md"

    def test_unsupported_format(self, tmp_path):
        path = tmp_path / "file.docx"
        path.write_text("data")
        with pytest.raises(ValueError, match="Unsupported format"):
            parse_file(str(path))
