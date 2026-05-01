import json
import zipfile

import pytest

import src.core.gutenberg_parser as gutenberg_parser
from src.core.gutenberg_parser import parse_gutenberg_zip


def test_parse_gutenberg_zip_strips_boilerplate_toc_and_footnotes(tmp_path):
    source_zip = tmp_path / "book.zip"
    output_dir = tmp_path / "book"
    html_text = """<!DOCTYPE html>
<html>
<head>
  <meta name="dc.title" content="The Prince">
  <meta name="dc.creator" content="Niccolò Machiavelli">
</head>
<body>
  <section class="pg-boilerplate pgheader" id="pg-header">
    <p>Title: The Prince</p>
    <div id="pg-start-separator">*** START OF THE PROJECT GUTENBERG EBOOK THE PRINCE ***</div>
  </section>
  <h1>The Prince</h1>
  <h2>by Nicolo Machiavelli</h2>
  <h2>Contents</h2>
  <table>
    <tr><td><a href="#chap1" class="pginternal">CHAPTER I</a></td></tr>
    <tr><td><a href="#chap2" class="pginternal">CHAPTER II</a></td></tr>
  </table>
  <div class="chapter">
    <h2><a id="chap1"></a>CHAPTER I</h2>
    <p>This is a paragraph that has been split
    across lines for Gutenberg formatting.</p>
    <p>Some text<a href="#fn-1" id="fnref-1" class="pginternal"><sup>[1]</sup></a>.</p>
    <p class="footnote"><a id="fn-1"></a><a href="#fnref-1">[1]</a> Footnote text.</p>
  </div>
  <div class="chapter">
    <h2><a id="chap2"></a>CHAPTER II</h2>
    <p>Second chapter text.</p>
  </div>
  <section class="pg-boilerplate pgfooter" id="pg-footer">
    <h2>THE FULL PROJECT GUTENBERG LICENSE</h2>
  </section>
</body>
</html>"""
    decoy_html = "<html><body><p>short decoy</p></body></html>"

    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("decoy.html", decoy_html)
        archive.writestr("pg1232-images.html", html_text)
        archive.writestr("cover.jpg", b"fake-cover")

    document = parse_gutenberg_zip(str(source_zip), str(output_dir), max_words_per_chapter=4000)

    assert document.title == "The Prince"
    assert document.author == "Niccolò Machiavelli"
    assert document.cover_filename == "cover.jpg"
    assert len(document.chapters) == 2
    assert document.chapters[0].title == "CHAPTER I"
    assert "Project Gutenberg" not in document.chapters[0].content
    assert "Footnote text" not in document.chapters[0].content
    assert "[1]" not in document.chapters[0].content
    assert "This is a paragraph that has been split across lines" in document.chapters[0].content

    report = json.loads((output_dir / "parse-report.json").read_text(encoding="utf-8"))
    assert report["selected_html_member"] == "pg1232-images.html"
    assert report["removed_boilerplate_sections"] >= 2
    assert report["removed_footnote_blocks"] == 1
    assert report["removed_footnote_refs"] >= 1
    assert report["fallback_split_used"] is False
    assert (output_dir / "source.cleaned.txt").exists()


def test_parse_gutenberg_zip_rejects_invalid_zip_file(tmp_path):
    source_zip = tmp_path / "broken.zip"
    source_zip.write_bytes(b"not a zip")

    with pytest.raises(zipfile.BadZipFile):
        parse_gutenberg_zip(str(source_zip))


def test_parse_gutenberg_zip_rejects_zip_without_safe_html_files(tmp_path):
    source_zip = tmp_path / "unsafe.zip"

    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("../pg1232-images.html", "<html><body><h1>Unsafe</h1></body></html>")
        archive.writestr("notes.txt", "plain text only")

    with pytest.raises(ValueError, match="Gutenberg HTML"):
        parse_gutenberg_zip(str(source_zip))


def test_parse_gutenberg_zip_uses_word_budget_fallback_without_chapter_markers(tmp_path):
    source_zip = tmp_path / "fallback.zip"
    output_dir = tmp_path / "book"
    html_text = """<!DOCTYPE html>
<html>
<head>
  <meta name="dc.title" content="Fallback Book">
  <meta name="dc.creator" content="Fallback Author">
</head>
<body>
  <h1>Fallback Book</h1>
  <p>By Fallback Author</p>
  <p>One two three four five six seven eight nine ten eleven twelve.</p>
  <p>Thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twenty-one twenty-two twenty-three twenty-four.</p>
</body>
</html>"""

    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("pg1232-images.html", html_text)

    document = parse_gutenberg_zip(str(source_zip), str(output_dir), max_words_per_chapter=12)
    report = json.loads((output_dir / "parse-report.json").read_text(encoding="utf-8"))

    assert document.title == "Fallback Book"
    assert document.author == "Fallback Author"
    assert len(document.chapters) == 2
    assert [chapter.title for chapter in document.chapters] == ["Chapter 1", "Chapter 2"]
    assert report["explicit_chapter_markers"] == 0
    assert report["fallback_split_used"] is True
    assert report["warnings"] == ["No explicit chapter markers found; fallback word-budget splitting used."]


def test_parse_gutenberg_zip_rejects_too_many_members(tmp_path, monkeypatch):
    source_zip = tmp_path / "too-many-members.zip"
    monkeypatch.setattr(gutenberg_parser, "MAX_GUTENBERG_ARCHIVE_MEMBERS", 2)

    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("pg1232-images.html", "<html><body><h1>Book</h1></body></html>")
        archive.writestr("notes.txt", "notes")
        archive.writestr("cover.jpg", b"cover")

    with pytest.raises(ValueError, match="too many members"):
        parse_gutenberg_zip(str(source_zip))


def test_parse_gutenberg_zip_rejects_excessive_uncompressed_size(tmp_path, monkeypatch):
    source_zip = tmp_path / "too-large-total.zip"
    monkeypatch.setattr(gutenberg_parser, "MAX_GUTENBERG_ARCHIVE_UNCOMPRESSED_SIZE", 40)

    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr(
            "pg1232-images.html",
            "<html><body><h1>Book</h1><p>1234567890</p></body></html>",
        )
        archive.writestr("notes.txt", "x" * 20)

    with pytest.raises(ValueError, match="size limit"):
        parse_gutenberg_zip(str(source_zip))


def test_parse_gutenberg_zip_rejects_oversized_html_member(tmp_path, monkeypatch):
    source_zip = tmp_path / "oversized-html.zip"
    monkeypatch.setattr(gutenberg_parser, "MAX_GUTENBERG_HTML_SIZE", 20)

    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("pg1232-images.html", "<html><body>this html is too large</body></html>")

    with pytest.raises(ValueError, match="HTML member 'pg1232-images.html' exceeds size limit"):
        parse_gutenberg_zip(str(source_zip))


def test_parse_gutenberg_zip_rejects_oversized_cover_image(tmp_path, monkeypatch):
    source_zip = tmp_path / "oversized-cover.zip"
    output_dir = tmp_path / "book"
    monkeypatch.setattr(gutenberg_parser, "MAX_GUTENBERG_COVER_SIZE", 5)

    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("pg1232-images.html", "<html><body><h1>Book</h1></body></html>")
        archive.writestr("cover.jpg", b"123456")

    with pytest.raises(ValueError, match="Cover image 'cover.jpg' exceeds size limit"):
        parse_gutenberg_zip(str(source_zip), str(output_dir))