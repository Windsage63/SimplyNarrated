from __future__ import annotations

from typing import Union

from src.core.docling_adapter import ImportedDocument, convert_pdf_document
from src.core.gutenberg_parser import parse_gutenberg_zip
from src.core.source_format import detect_format
from src.core.text_parser import ParsedTextDocument, parse_text_document

MAX_WORDS_PER_CHAPTER = 4000


def convert_source_document(
    file_path: str,
    output_dir: str | None = None,
    max_words_per_chapter: int = MAX_WORDS_PER_CHAPTER,
) -> Union[ImportedDocument, ParsedTextDocument]:
    """Route a source document to the correct import pipeline."""
    format_type = detect_format(file_path)

    if format_type == "txt":
        return parse_text_document(
            file_path,
            output_dir=output_dir,
            max_words_per_chapter=max_words_per_chapter,
        )

    if format_type == "zip":
        return parse_gutenberg_zip(
            file_path,
            output_dir=output_dir,
            max_words_per_chapter=max_words_per_chapter,
        )

    if format_type == "pdf":
        return convert_pdf_document(
            file_path,
            output_dir=output_dir,
            max_words_per_chapter=max_words_per_chapter,
        )

    raise ValueError(f"Unsupported format: {format_type}")