from src.core.docling_adapter import _extract_cover_from_pdf, _prepare_source_for_docling, _resolve_author


def test_prepare_source_for_docling_keeps_pdf_unchanged(pdf_factory):
    pdf_path = pdf_factory("identity.pdf")

    prepared = _prepare_source_for_docling(str(pdf_path))

    assert prepared.path == str(pdf_path)
    assert prepared.format_type == "pdf"
    assert prepared.cleanup_dir is None


def test_resolve_author_reads_real_pdf_metadata(pdf_factory):
    pdf_path = pdf_factory("author.pdf", author="Jane PDF")

    author = _resolve_author(str(pdf_path), "pdf")

    assert author == "Jane PDF"


def test_resolve_author_returns_none_for_non_pdf(pdf_factory):
    pdf_path = pdf_factory("author.pdf", author="Ignored")

    author = _resolve_author(str(pdf_path), "txt")

    assert author is None


def test_extract_cover_from_pdf_writes_cover_file(pdf_factory, tmp_path):
    pdf_path = pdf_factory("cover.pdf", include_cover=True)

    cover_filename = _extract_cover_from_pdf(str(pdf_path), str(tmp_path))

    assert cover_filename in {"cover.png", "cover.jpg"}
    assert (tmp_path / cover_filename).exists()


def test_extract_cover_from_pdf_returns_none_without_images(pdf_factory, tmp_path):
    pdf_path = pdf_factory("no-cover.pdf", include_cover=False)

    cover_filename = _extract_cover_from_pdf(str(pdf_path), str(tmp_path))

    assert cover_filename is None