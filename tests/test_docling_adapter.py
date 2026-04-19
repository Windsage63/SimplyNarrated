"""
Tests for the Docling adapter import pipeline.
"""

import zipfile

import pytest

from src.core.docling_adapter import (
    _strip_gutenberg_boilerplate,
    _normalize_gutenberg_paragraph_wrapping,
    _prepare_source_for_docling,
    convert_source_document,
)


WRAPPED_GUTENBERG_HTML = """\
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Metamorphosis | Project Gutenberg</title>
</head><body>
<div class="chapter"><h2>Chapter 1</h2>
<p>
One morning, when Gregor Samsa woke from troubled dreams, he found himself
transformed in his bed into a horrible vermin. He lay on his armour-like back,
and if he lifted his head a little he could see his brown belly, slightly domed
and divided by arches into stiff sections.
</p>
</div>
</body></html>
"""

WRAPPED_GUTENBERG_HTML_WITH_BLANK_LINES = """\
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>A Princess of Mars | Project Gutenberg</title>
</head><body>
<div class="chapter"><h2>Chapter 3</h2>
<p>
They have decided to carry her with us back to Thark, and exhibit her

last agonies at the great games before Tal Hajus, replied Sarkoja.
What will be the manner of her going out? inquired Sola. She is very

small and very beautiful; I had hoped that they would hold her for ransom.
</p>
</div>
</body></html>
"""

WRAPPED_GUTENBERG_TWO_LINE_PROSE_HTML = """\
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>A Princess of Mars | Project Gutenberg</title>
</head><body>
<div class="chapter"><h2>Chapter 3</h2>
<p>
They have decided to carry her with us back to Thark, and exhibit her
last agonies at the great games before Tal Hajus,” replied Sarkoja.
</p>
<p>
Sarkoja and the other women grunted angrily at this evidence of weakness on the
part of Sola.
</p>
</div>
</body></html>
"""

MIXED_GUTENBERG_DIALOGUE_HTML = """\
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>The Gods of Mars | Project Gutenberg</title>
</head><body>
<div class="chapter"><h2>Chapter 1</h2>
<p>
On the raised platform of the throne was Tardos Mors, pacing back and forth
with tense-drawn face. When all were in their seats he turned toward us.
</p>
<p>
“This morning,” he said, “word reached the several
governments of Barsoom that the keeper of the atmosphere plant had made no
wireless report for two days, nor had almost ceaseless calls upon him from a
score of capitals elicited a sign of response.
</p>
<p>
“The ambassadors of the other nations asked us to take the matter in hand
and hasten the assistant keeper to the plant. All day a thousand cruisers have
been searching for him until just now one of them returns bearing his dead
body, which was found in the pits beneath his house horribly mutilated by some
assassin.
</p>
<p>
“I do not need to tell you what this means to Barsoom. It would take
months to penetrate those mighty walls, in fact the work has already commenced,
and there would be little to fear were the engine of the pumping plant to run
as it should and as they all have for hundreds of years; but the worst, we
fear, has happened. The instruments show a rapidly decreasing air pressure on
all parts of Barsoom—the engine has stopped.”
</p>
<p>
“My gentlemen,” he concluded, “we have at best three days to
live.”
</p>
<p>
There was absolute silence for several minutes, and then a young noble arose,
and with his drawn sword held high above his head addressed Tardos Mors.
</p>
</div>
</body></html>
"""

PG_FOOTER_BOILERPLATE_HTML = """\
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"></head><body>
<div class="chapter"><h2>Chapter 1</h2>
<p>
This is the final paragraph of the book and should remain.
</p>
</div>
<div></div><section class="pg-boilerplate pgheader" id="pg-footer" lang="en">
<div id="pg-end-separator">
<span>*** END OF THE PROJECT GUTENBERG EBOOK A PRINCESS OF MARS ***</span>
</div>
<div>This boilerplate text should be removed before Docling sees it.</div>
</section>
</body></html>
"""

SHORT_TWO_LINE_HTML = """\
<p>
Chapter III
The Escape
</p>
"""

VERSE_LIKE_HTML = """\
<p>
I saw the river run
Through fields of winter snow,
And heard the distant chapel bell
Above the cedars blow.
</p>
"""


class TestNormalizeGutenbergParagraphWrapping:
    def test_reflows_wrapped_prose_paragraphs(self):
        normalized = _normalize_gutenberg_paragraph_wrapping(WRAPPED_GUTENBERG_HTML)

        assert "found himself transformed in his bed" in normalized
        assert "back, and if he lifted his head" in normalized
        assert "found himself\ntransformed" not in normalized

    def test_preserves_short_verse_like_paragraphs(self):
        normalized = _normalize_gutenberg_paragraph_wrapping(VERSE_LIKE_HTML)

        assert "I saw the river run\nThrough fields of winter snow," in normalized

    def test_reflows_wrapped_prose_paragraphs_with_blank_formatting_lines(self):
        normalized = _normalize_gutenberg_paragraph_wrapping(WRAPPED_GUTENBERG_HTML_WITH_BLANK_LINES)

        assert "exhibit her last agonies at the great games" in normalized
        assert "very\nsmall and very beautiful" not in normalized
        assert "exhibit her\n\nlast agonies" not in normalized

    def test_reflows_two_line_wrapped_prose_paragraphs(self):
        normalized = _normalize_gutenberg_paragraph_wrapping(WRAPPED_GUTENBERG_TWO_LINE_PROSE_HTML)

        assert "exhibit her last agonies at the great games" in normalized
        assert "weakness on the part of Sola." in normalized
        assert "exhibit her\nlast agonies" not in normalized
        assert "weakness on the\npart of Sola." not in normalized

    def test_reflows_mixed_dialogue_and_prose_paragraphs(self):
        normalized = _normalize_gutenberg_paragraph_wrapping(MIXED_GUTENBERG_DIALOGUE_HTML)

        assert "word reached the several governments of Barsoom" in normalized
        assert "we have at best three days to live." in normalized
        assert 'several\ngovernments of Barsoom' not in normalized
        assert 'days to\nlive.' not in normalized

    def test_does_not_reflow_short_two_line_heading_like_text(self):
        normalized = _normalize_gutenberg_paragraph_wrapping(SHORT_TWO_LINE_HTML)

        assert "Chapter III\nThe Escape" in normalized


class TestStripGutenbergBoilerplate:
    def test_strips_footer_boilerplate_section_and_separator(self):
        normalized = _strip_gutenberg_boilerplate(PG_FOOTER_BOILERPLATE_HTML)

        assert "This is the final paragraph of the book and should remain." in normalized
        assert "*** END OF THE PROJECT GUTENBERG EBOOK" not in normalized
        assert "This boilerplate text should be removed" not in normalized


class TestConvertSourceDocument:
    def test_txt_import_creates_multiple_chapters(self, sample_txt_file, tmp_path):
        document = convert_source_document(sample_txt_file, str(tmp_path))

        assert document.format == "txt"
        assert document.title == "My Test Book"
        assert len(document.chapters) >= 2
        assert any("Chapter 1" in chapter.title for chapter in document.chapters)
        assert any(chapter.chunks for chapter in document.chapters)

    def test_markdown_import_uses_heading_structure(self, sample_md_file, tmp_path):
        document = convert_source_document(sample_md_file, str(tmp_path))

        assert document.format == "md"
        assert document.title == "My Markdown Book"
        assert len(document.chapters) >= 2
        assert document.chapters[0].title == "Chapter One"
        assert document.chapters[1].title == "Chapter Two"

    def test_zip_import_extracts_cover_and_chapters(self, sample_zip_file, tmp_path):
        document = convert_source_document(sample_zip_file, str(tmp_path))

        assert document.format == "zip"
        assert document.cover_filename == "cover.png"
        assert len(document.chapters) >= 2
        assert any("Chapter 1" in chapter.title for chapter in document.chapters)

    def test_pdf_import_returns_document(self, sample_pdf_file, tmp_path):
        document = convert_source_document(sample_pdf_file, str(tmp_path))

        assert document.format == "pdf"
        assert document.title
        assert len(document.chapters) >= 1

    def test_zip_import_reflows_wrapped_gutenberg_paragraphs(self, tmp_uploads_dir, tmp_path):
        path = tmp_uploads_dir / "wrapped_gutenberg.zip"
        with zipfile.ZipFile(str(path), "w") as archive:
            archive.writestr("pg12345-images.html", WRAPPED_GUTENBERG_HTML)

        document = convert_source_document(str(path), str(tmp_path))

        chapter_text = "\n".join(
            chunk.text
            for chapter in document.chapters
            for chunk in chapter.chunks
        )

        assert "found himself transformed in his bed" in chapter_text
        assert "found himself\ntransformed" not in chapter_text

    def test_zip_import_reflows_wrapped_gutenberg_paragraphs_with_blank_lines(self, tmp_uploads_dir, tmp_path):
        path = tmp_uploads_dir / "wrapped_gutenberg_blank_lines.zip"
        with zipfile.ZipFile(str(path), "w") as archive:
            archive.writestr("pg12345-images.html", WRAPPED_GUTENBERG_HTML_WITH_BLANK_LINES)

        document = convert_source_document(str(path), str(tmp_path))

        chapter_text = "\n".join(
            chunk.text
            for chapter in document.chapters
            for chunk in chapter.chunks
        )

        assert "exhibit her last agonies at the great games" in chapter_text
        assert "very small and very beautiful" in chapter_text
        assert "exhibit her\n\nlast agonies" not in chapter_text

    def test_zip_import_reflows_two_line_wrapped_gutenberg_paragraphs(self, tmp_uploads_dir, tmp_path):
        path = tmp_uploads_dir / "wrapped_gutenberg_two_line.zip"
        with zipfile.ZipFile(str(path), "w") as archive:
            archive.writestr("pg12345-images.html", WRAPPED_GUTENBERG_TWO_LINE_PROSE_HTML)

        document = convert_source_document(str(path), str(tmp_path))

        chapter_text = "\n".join(
            chunk.text
            for chapter in document.chapters
            for chunk in chapter.chunks
        )

        assert "exhibit her last agonies at the great games" in chapter_text
        assert "weakness on the part of Sola." in chapter_text
        assert "exhibit her\nlast agonies" not in chapter_text
        assert "weakness on the\npart of Sola." not in chapter_text

    def test_zip_import_reflows_mixed_dialogue_and_prose_paragraphs(self, tmp_uploads_dir, tmp_path):
        path = tmp_uploads_dir / "wrapped_gutenberg_dialogue.zip"
        with zipfile.ZipFile(str(path), "w") as archive:
            archive.writestr("pg12345-images.html", MIXED_GUTENBERG_DIALOGUE_HTML)

        document = convert_source_document(str(path), str(tmp_path))

        chapter_text = "\n".join(
            chunk.text
            for chapter in document.chapters
            for chunk in chapter.chunks
        )

        assert "word reached the several governments of Barsoom" in chapter_text
        assert "we have at best three days to live." in chapter_text
        assert 'several\ngovernments of Barsoom' not in chapter_text
        assert 'days to\nlive.' not in chapter_text

    def test_zip_import_strips_pg_footer_boilerplate(self, tmp_uploads_dir, tmp_path):
        path = tmp_uploads_dir / "wrapped_gutenberg_footer.zip"
        with zipfile.ZipFile(str(path), "w") as archive:
            archive.writestr("pg12345-images.html", PG_FOOTER_BOILERPLATE_HTML)

        document = convert_source_document(str(path), str(tmp_path))

        chapter_text = "\n".join(
            chunk.text
            for chapter in document.chapters
            for chunk in chapter.chunks
        )

        assert "This is the final paragraph of the book and should remain." in chapter_text
        assert "*** END OF THE PROJECT GUTENBERG EBOOK" not in chapter_text
        assert "This boilerplate text should be removed" not in chapter_text


class TestPrepareSourceRejectsStandaloneHtml:
    def test_html_extension_raises_value_error(self, tmp_path):
        html_file = tmp_path / "sample.html"
        html_file.write_text("<html><body>Hello</body></html>", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported format: html"):
            _prepare_source_for_docling(str(html_file))

    def test_htm_extension_raises_value_error(self, tmp_path):
        htm_file = tmp_path / "sample.htm"
        htm_file.write_text("<html><body>Hello</body></html>", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported format: htm"):
            _prepare_source_for_docling(str(htm_file))