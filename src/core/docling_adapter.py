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
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from typing import List, Optional, Tuple

from docling.chunking import HierarchicalChunker
from docling.document_converter import DocumentConverter

from src.core.text_parser import ParsedTextDocument, parse_text_document

logger = logging.getLogger(__name__)

MAX_WORDS_PER_CHAPTER = 4000
GUTENBERG_PROSE_MIN_FIRST_LINE_LENGTH = 49
GUTENBERG_PROSE_MIN_FIRST_TWO_LINES_TOTAL = 79


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


@dataclass(frozen=True)
class _PreparedSource:
    path: str
    format_type: str
    cleanup_dir: Optional[str] = None


def convert_source_document(
    file_path: str,
    output_dir: Optional[str] = None,
    max_words_per_chapter: int = MAX_WORDS_PER_CHAPTER,
) -> ImportedDocument | ParsedTextDocument:
    """Convert a source file to a Docling-backed imported document."""
    prepared = _prepare_source_for_docling(file_path)

    if prepared.format_type == "txt":
        return parse_text_document(
            file_path,
            output_dir=output_dir,
            max_words_per_chapter=max_words_per_chapter,
        )

    try:
        converter = DocumentConverter()
        result = converter.convert(prepared.path)
        docling_document = result.document

        docling_chunks = _extract_docling_chunks(docling_document)
        document_title = _resolve_document_title(file_path, prepared.format_type, docling_chunks)
        chapters = _build_imported_chapters(
            docling_chunks,
            document_title=document_title,
            max_words_per_chapter=max_words_per_chapter,
        )
        cover_filename = extract_cover_image(file_path, output_dir) if output_dir else None

        return ImportedDocument(
            title=document_title,
            author=_resolve_author(file_path, prepared.format_type),
            format=prepared.format_type,
            chapters=chapters,
            cover_filename=cover_filename,
        )
    finally:
        if prepared.cleanup_dir:
            shutil.rmtree(prepared.cleanup_dir, ignore_errors=True)


def extract_cover_image(file_path: str, output_dir: str) -> Optional[str]:
    """Extract a cover image from supported source formats."""
    format_type = detect_format(file_path)

    if format_type == "pdf":
        return _extract_cover_from_pdf(file_path, output_dir)
    if format_type == "md":
        return _extract_cover_from_markdown(file_path, output_dir)
    if format_type == "zip":
        return _extract_cover_from_zip(file_path, output_dir)
    return None


def detect_format(file_path: str) -> str:
    """Detect a supported format from file extension."""
    return os.path.splitext(file_path)[1].lower().lstrip(".")


def count_words(text: str) -> int:
    """Count words in a text block."""
    return len(text.split())


def _prepare_source_for_docling(file_path: str) -> _PreparedSource:
    format_type = detect_format(file_path)

    if format_type in {"md", "pdf", "txt"}:
        return _PreparedSource(path=file_path, format_type=format_type)

    temp_dir = tempfile.mkdtemp(prefix="simplynarrated-docling-")

    if format_type == "zip":
        prepared_path = _extract_html_from_zip_to_temp(file_path, temp_dir)
        return _PreparedSource(path=prepared_path, format_type="zip", cleanup_dir=temp_dir)

    shutil.rmtree(temp_dir, ignore_errors=True)
    raise ValueError(f"Unsupported format: {format_type}")


def _extract_html_from_zip_to_temp(file_path: str, temp_dir: str) -> str:
    with zipfile.ZipFile(file_path) as archive:
        html_members = [
            member
            for member in archive.infolist()
            if not member.is_dir()
            and _safe_zip_member(member.filename)
            and member.filename.lower().endswith((".html", ".htm"))
        ]

        if not html_members:
            raise ValueError("ZIP does not contain any HTML files")

        largest_html = max(html_members, key=lambda member: member.file_size)
        html_text = archive.read(largest_html.filename).decode("utf-8", errors="ignore")

    prepared_path = os.path.join(temp_dir, "gutenberg.html")
    with open(prepared_path, "w", encoding="utf-8") as prepared_file:
        prepared_file.write(_normalize_gutenberg_html(html_text))
    return prepared_path


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


def _resolve_author(file_path: str, format_type: str) -> Optional[str]:
    if format_type != "pdf":
        return None

    try:
        import pymupdf
    except ImportError:
        return None

    try:
        document = pymupdf.open(file_path)
        author = document.metadata.get("author")
        document.close()
        return author or None
    except Exception:
        logger.warning("Failed to extract PDF author metadata", exc_info=True)
        return None


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


def _safe_zip_member(name: str) -> bool:
    if name.startswith("/") or ".." in name.split("/"):
        return False
    return True


def _strip_gutenberg_boilerplate(html_text: str) -> str:
    html_text = re.sub(
        r'<section[^>]*class=["\'][^"\']*pg-boilerplate[^"\']*["\'][^>]*>.*?</section>',
        "",
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_text = re.sub(
        r'<(?:div|section)[^>]*id=["\']pg-header["\'][^>]*>.*?</(?:div|section)>',
        "",
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_text = re.sub(
        r'<(?:div|section)[^>]*id=["\']pg-footer["\'][^>]*>.*?</(?:div|section)>',
        "",
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_text = re.sub(
        r'<div[^>]*id=["\']pg-(?:start|end)-separator["\'][^>]*>.*?</div>',
        "",
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html_text


def _normalize_gutenberg_html(html_text: str) -> str:
    cleaned_html = _strip_gutenberg_boilerplate(html_text)
    return _normalize_gutenberg_paragraph_wrapping(cleaned_html)


def _normalize_gutenberg_paragraph_wrapping(html_text: str) -> str:
    return re.sub(
        r"(<p\b[^>]*>)(.*?)(</p>)",
        _reflow_gutenberg_paragraph_match,
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )


def _reflow_gutenberg_paragraph_match(match: re.Match[str]) -> str:
    opening_tag, paragraph_body, closing_tag = match.groups()
    if not _looks_like_wrapped_gutenberg_prose(paragraph_body):
        return match.group(0)

    reflowed_lines = [line.strip() for line in paragraph_body.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    reflowed_body = " ".join(line for line in reflowed_lines if line)
    return f"{opening_tag}{reflowed_body}{closing_tag}"


def _looks_like_wrapped_gutenberg_prose(paragraph_body: str) -> bool:
    visible_text = re.sub(r"<[^>]+>", "", paragraph_body)
    normalized_text = visible_text.replace("\r\n", "\n").replace("\r", "\n")

    if "\n" not in normalized_text:
        return False

    raw_lines = normalized_text.split("\n")
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()

    if not raw_lines:
        return False

    non_empty_lines = [line.strip() for line in raw_lines if line.strip()]

    if len(non_empty_lines) < 2:
        return False

    first_line_length = len(non_empty_lines[0])
    first_two_lines_total = len(non_empty_lines[0]) + len(non_empty_lines[1])

    if first_line_length < GUTENBERG_PROSE_MIN_FIRST_LINE_LENGTH:
        return False
    if len(non_empty_lines) > 2 and first_two_lines_total < GUTENBERG_PROSE_MIN_FIRST_TWO_LINES_TOTAL:
        return False

    continuation_count = sum(
        1
        for left_line, right_line in zip(non_empty_lines, non_empty_lines[1:])
        if _looks_like_prose_continuation(left_line, right_line)
    )
    return continuation_count >= 1


def _looks_like_prose_continuation(left_line: str, right_line: str) -> bool:
    if not right_line:
        return False

    if right_line[0].islower() or right_line[0] in {'"', "'", "(", "[", "-"}:
        return True

    return not bool(re.search(r"[.!?][\"'”’)]?$", left_line))


def _extract_cover_from_pdf(file_path: str, output_dir: str) -> Optional[str]:
    try:
        import pymupdf
    except ImportError:
        return None

    try:
        document = pymupdf.open(file_path)
        if len(document) == 0:
            document.close()
            return None

        page = document[0]
        images = page.get_images(full=True)
        if not images:
            document.close()
            return None

        xref = images[0][0]
        base_image = document.extract_image(xref)
        document.close()

        if not base_image or not base_image.get("image"):
            return None

        image_ext = base_image.get("ext", "png").lower()
        cover_filename = "cover.jpg" if image_ext in {"jpg", "jpeg"} else "cover.png"
        cover_path = os.path.join(output_dir, cover_filename)
        with open(cover_path, "wb") as cover_file:
            cover_file.write(base_image["image"])
        return cover_filename
    except Exception:
        logger.warning("Failed to extract PDF cover image", exc_info=True)
        return None


def _extract_cover_from_markdown(file_path: str, output_dir: str) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as markdown_file:
            content = markdown_file.read()

        match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", content)
        if not match:
            return None

        image_ref = match.group(1).strip()
        if image_ref.startswith(("http://", "https://", "ftp://", "data:", "//")):
            return None

        source_dir = os.path.dirname(os.path.abspath(file_path))
        image_path = os.path.normpath(os.path.join(source_dir, image_ref))
        if os.path.commonpath([source_dir, image_path]) != source_dir:
            return None
        if not os.path.isfile(image_path):
            return None

        extension = os.path.splitext(image_path)[1].lower()
        if extension in {".jpg", ".jpeg"}:
            cover_filename = "cover.jpg"
        elif extension == ".png":
            cover_filename = "cover.png"
        else:
            return None

        shutil.copy2(image_path, os.path.join(output_dir, cover_filename))
        return cover_filename
    except Exception:
        logger.warning("Failed to extract markdown cover image", exc_info=True)
        return None


def _extract_cover_from_zip(file_path: str, output_dir: str) -> Optional[str]:
    try:
        with zipfile.ZipFile(file_path) as archive:
            image_members = [
                member
                for member in archive.infolist()
                if not member.is_dir()
                and _safe_zip_member(member.filename)
                and member.filename.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            cover_member = None
            for member in image_members:
                if "cover" in os.path.basename(member.filename).lower():
                    cover_member = member
                    break

            if not cover_member:
                return None

            extension = os.path.splitext(cover_member.filename)[1].lower()
            cover_filename = "cover.jpg" if extension in {".jpg", ".jpeg"} else "cover.png"
            with open(os.path.join(output_dir, cover_filename), "wb") as cover_file:
                cover_file.write(archive.read(cover_member.filename))
            return cover_filename
    except Exception:
        logger.warning("Failed to extract ZIP cover image", exc_info=True)
        return None