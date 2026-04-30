from src.core.docling_adapter import ImportedDocument
from src.core.document_router import convert_source_document
from src.core.text_parser import ParsedTextChapter, ParsedTextDocument


def test_convert_source_document_routes_txt(monkeypatch, tmp_path):
    source_path = tmp_path / "input.txt"
    source_path.write_text("hello", encoding="utf-8")
    expected = ParsedTextDocument(
        title="TXT",
        author=None,
        format="txt",
        chapters=[ParsedTextChapter(number=1, title="Chapter 1", content="hello")],
    )
    calls = {}

    def fake_parse_text_document(file_path, output_dir=None, max_words_per_chapter=4000):
        calls["txt"] = (file_path, output_dir, max_words_per_chapter)
        return expected

    monkeypatch.setattr("src.core.document_router.parse_text_document", fake_parse_text_document)

    result = convert_source_document(str(source_path), output_dir="book-dir", max_words_per_chapter=123)

    assert result is expected
    assert calls["txt"] == (str(source_path), "book-dir", 123)


def test_convert_source_document_routes_zip(monkeypatch, tmp_path):
    source_path = tmp_path / "input.zip"
    source_path.write_bytes(b"PK\x03\x04")
    expected = ParsedTextDocument(
        title="ZIP",
        author=None,
        format="zip",
        chapters=[ParsedTextChapter(number=1, title="Chapter 1", content="hello")],
    )
    calls = {}

    def fake_parse_gutenberg_zip(file_path, output_dir=None, max_words_per_chapter=4000):
        calls["zip"] = (file_path, output_dir, max_words_per_chapter)
        return expected

    monkeypatch.setattr("src.core.document_router.parse_gutenberg_zip", fake_parse_gutenberg_zip)

    result = convert_source_document(str(source_path), output_dir="book-dir", max_words_per_chapter=123)

    assert result is expected
    assert calls["zip"] == (str(source_path), "book-dir", 123)


def test_convert_source_document_routes_pdf(monkeypatch, tmp_path):
    source_path = tmp_path / "input.pdf"
    source_path.write_bytes(b"%PDF-1.4")
    expected = ImportedDocument(title="PDF", author=None, format="pdf", chapters=[])
    calls = {}

    def fake_convert_pdf_document(file_path, output_dir=None, max_words_per_chapter=4000):
        calls["pdf"] = (file_path, output_dir, max_words_per_chapter)
        return expected

    monkeypatch.setattr("src.core.document_router.convert_pdf_document", fake_convert_pdf_document)

    result = convert_source_document(str(source_path), output_dir="book-dir", max_words_per_chapter=123)

    assert result is expected
    assert calls["pdf"] == (str(source_path), "book-dir", 123)