from pathlib import Path

import pytest

from src.core.docling_adapter import ImportedDocument, convert_pdf_document


FIXTURE_PDF = Path(__file__).with_name("fixtures") / "The GeoPilotical Chess Game.pdf"


def test_convert_pdf_document_rejects_non_pdf(tmp_path):
    source_path = tmp_path / "identity.txt"
    source_path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(ValueError, match="PDF"):
        convert_pdf_document(str(source_path))


def test_convert_pdf_document_returns_no_author_or_cover(monkeypatch, tmp_path):
    pdf_path = FIXTURE_PDF

    class FakeResult:
        def __init__(self, document):
            self.document = document

    class FakeDoclingDocument:
        def export_to_markdown(self):
            return "# Sample PDF\n\nHello world"

    class FakeConverter:
        def convert(self, file_path):
            assert file_path == str(pdf_path)
            return FakeResult(FakeDoclingDocument())

    monkeypatch.setattr("src.core.docling_adapter.DocumentConverter", lambda: FakeConverter())
    monkeypatch.setattr(
        "src.core.docling_adapter._extract_docling_chunks",
        lambda document: [],
    )

    result = convert_pdf_document(str(pdf_path), output_dir=str(tmp_path))

    assert isinstance(result, ImportedDocument)
    assert result.author is None
    assert result.cover_filename is None