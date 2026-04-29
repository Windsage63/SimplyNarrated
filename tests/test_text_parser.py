import json

from src.core.text_parser import parse_text_document


def test_parse_text_document_creates_cleaned_artifacts_and_chapters(tmp_path):
    source_path = tmp_path / "sample.txt"
    output_dir = tmp_path / "book"
    source_path.write_text(
        "Sample Book\n\nBy Jane Parser\n\nCHAPTER 1\n\nThis is a wrapped line that should be joined\nwith the next line into a single paragraph.\n\nCHAPTER 2\n\nSecond chapter text.",
        encoding="utf-8",
    )

    document = parse_text_document(str(source_path), str(output_dir), max_words_per_chapter=4000)

    assert document.title == "Sample Book"
    assert document.author == "Jane Parser"
    assert len(document.chapters) == 2
    assert document.chapters[0].title == "CHAPTER 1"
    assert "joined with the next line" in document.chapters[0].content
    assert (output_dir / "source.cleaned.txt").exists()
    assert (output_dir / "parse-report.json").exists()

    report = json.loads((output_dir / "parse-report.json").read_text(encoding="utf-8"))
    assert report["chapter_count"] == 2
    assert report["fallback_split_used"] is False


def test_parse_text_document_uses_fallback_splitting_without_chapter_markers(tmp_path):
    source_path = tmp_path / "fallback.txt"
    output_dir = tmp_path / "fallback-book"
    source_path.write_text(
        "Untitled Source\n\nThis is the first paragraph.\n\nThis is the second paragraph with more words.",
        encoding="utf-8",
    )

    document = parse_text_document(str(source_path), str(output_dir), max_words_per_chapter=5)

    assert len(document.chapters) >= 2
    assert document.chapters[0].title == "Chapter 1"
    report = json.loads((output_dir / "parse-report.json").read_text(encoding="utf-8"))
    assert report["fallback_split_used"] is True
    assert report["warnings"]