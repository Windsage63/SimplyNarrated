"""
@fileoverview SimplyNarrated - Docling adapter, Import-time document conversion and chapter grouping
@author Timothy Mallory <windsage@live.com>
@license Apache-2.0
@copyright 2026 Timothy Mallory <windsage@live.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

from docling.chunking import HierarchicalChunker
from docling.document_converter import DocumentConverter
from src.core.source_format import detect_format

logger = logging.getLogger(__name__)

MAX_WORDS_PER_CHAPTER = 4000


@dataclass(frozen=True)
class ImportedChunk:
    """Single Docling-derived chunk with heading context."""

    text: str
    headings: List[str]


@dataclass(frozen=True)
class ImportedChapter:
    """Logical chapter prepared from Docling chunks."""

    number: int
    title: str
    chunks: List[ImportedChunk]


@dataclass(frozen=True)
class ImportedDocument:
    """Document prepared for speech rendering and synthesis."""

    title: str
    author: Optional[str]
    format: str
    chapters: List[ImportedChapter]
    cover_filename: Optional[str] = None


def convert_pdf_document(
    file_path: str,
    output_dir: Optional[str] = None,
    max_words_per_chapter: int = MAX_WORDS_PER_CHAPTER,
) -> ImportedDocument:
    """Convert a PDF source file to an imported document via Docling."""
    format_type = detect_format(file_path)
    if format_type != "pdf":
        raise ValueError(f"Docling PDF converter only supports PDF files, got: {format_type}")

    converter = DocumentConverter()
    result = converter.convert(file_path)
    docling_document = result.document

    docling_chunks = _extract_docling_chunks(docling_document)
    document_title = _resolve_document_title(file_path, format_type, docling_chunks)
    chapters = _build_imported_chapters(
        docling_chunks,
        document_title=document_title,
        max_words_per_chapter=max_words_per_chapter,
    )

    return ImportedDocument(
        title=document_title,
        author=None,
        format=format_type,
        chapters=chapters,
        cover_filename=None,
    )


def count_words(text: str) -> int:
    """Count words in a text block."""
    return len(text.split())


def _extract_docling_chunks(docling_document) -> List[ImportedChunk]:
    chunker = HierarchicalChunker()
    imported_chunks: List[ImportedChunk] = []

    for chunk in chunker.chunk(docling_document):
        chunk_text = getattr(chunk, "text", "") or ""
        headings = list(getattr(getattr(chunk, "meta", None), "headings", []) or [])
        normalized_text = chunk_text.strip()
        if normalized_text:
            imported_chunks.append(
                ImportedChunk(
                    text=normalized_text,
                    headings=[heading.strip() for heading in headings if heading and heading.strip()],
                )
            )

    if not imported_chunks:
        markdown_text = docling_document.export_to_markdown().strip()
        if markdown_text:
            imported_chunks.append(ImportedChunk(text=markdown_text, headings=[]))

    return imported_chunks


def _resolve_document_title(
    file_path: str,
    format_type: str,
    docling_chunks: List[ImportedChunk],
) -> str:
    if docling_chunks:
        headings = docling_chunks[0].headings
        if headings:
            return headings[0]

    if format_type == "txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as source_file:
            for line in source_file:
                stripped = line.strip()
                if stripped:
                    if len(stripped) <= 120:
                        return stripped
                    break

    return os.path.splitext(os.path.basename(file_path))[0]


def _build_imported_chapters(
    docling_chunks: List[ImportedChunk],
    document_title: str,
    max_words_per_chapter: int,
) -> List[ImportedChapter]:
    raw_groups: List[Tuple[str, List[ImportedChunk]]] = []

    for chunk in docling_chunks:
        group_title = _determine_group_title(chunk, document_title)
        if raw_groups and raw_groups[-1][0] == group_title:
            raw_groups[-1][1].append(chunk)
        else:
            raw_groups.append((group_title, [chunk]))

    chapters: List[ImportedChapter] = []
    chapter_number = 1
    untitled_count = 1

    for base_title, group_chunks in raw_groups:
        title = base_title or f"Chapter {untitled_count}"
        if not base_title:
            untitled_count += 1

        parts = _split_group_by_word_budget(group_chunks, max_words_per_chapter)
        multi_part = len(parts) > 1

        for index, part_chunks in enumerate(parts, start=1):
            chapter_title = title if not multi_part else f"{title} (Part {index})"
            chapters.append(
                ImportedChapter(
                    number=chapter_number,
                    title=chapter_title,
                    chunks=part_chunks,
                )
            )
            chapter_number += 1

    return chapters or [ImportedChapter(number=1, title="Chapter 1", chunks=[])]


def _determine_group_title(chunk: ImportedChunk, document_title: str) -> str:
    headings = [heading for heading in chunk.headings if heading]
    if not headings:
        return ""

    if headings and headings[0].casefold() == document_title.casefold():
        headings = headings[1:]

    return headings[0] if headings else ""


def _split_group_by_word_budget(
    group_chunks: List[ImportedChunk],
    max_words_per_chapter: int,
) -> List[List[ImportedChunk]]:
    if not group_chunks:
        return [[]]

    parts: List[List[ImportedChunk]] = []
    current_part: List[ImportedChunk] = []
    current_words = 0

    for chunk in group_chunks:
        chunk_words = count_words(chunk.text)
        if current_part and current_words + chunk_words > max_words_per_chapter:
            parts.append(current_part)
            current_part = []
            current_words = 0

        current_part.append(chunk)
        current_words += chunk_words

    if current_part:
        parts.append(current_part)

    return parts
