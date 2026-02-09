"""
@fileoverview BookTalk - File Parser, Extract and normalize text from various file formats
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

import os
import re
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class ParsedDocument:
    """Represents a parsed document with extracted content."""

    title: str
    author: Optional[str]
    raw_text: str
    chapters: List[Tuple[str, str]]  # List of (title, content) tuples
    format: str


def detect_format(file_path: str) -> str:
    """Detect the file format from extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext.lstrip(".")


def parse_txt(file_path: str) -> ParsedDocument:
    """Parse a plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Try to extract title from first line
    lines = content.strip().split("\n")
    title = lines[0].strip() if lines else "Untitled"
    if len(title) > 100:
        title = os.path.splitext(os.path.basename(file_path))[0]

    # Simple chapter detection for TXT files
    chapters = _split_into_chapters(content)

    # Normalize each chapter's content to remove single line breaks
    normalized_chapters = []
    for ch_title, ch_content in chapters:
        normalized_chapters.append((ch_title, _normalize_line_breaks(ch_content)))

    # Reconstruct normalized raw text
    full_text = "\n\n".join([f"{t}\n\n{c}" for t, c in normalized_chapters])

    return ParsedDocument(
        title=title,
        author=None,
        raw_text=full_text,
        chapters=normalized_chapters,
        format="txt",
    )


def parse_markdown(file_path: str) -> ParsedDocument:
    """Parse a Markdown file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Extract title from first h1
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled"

    # Split by h1 or h2 headings as chapters
    chapters = _split_markdown_chapters(content)

    # Convert markdown to plain text
    plain_text = _markdown_to_text(content)

    return ParsedDocument(
        title=title,
        author=None,
        raw_text=plain_text,
        chapters=chapters,
        format="md",
    )


def parse_epub(file_path: str) -> ParsedDocument:
    """Parse an EPUB file."""
    try:
        import ebooklib
        from ebooklib import epub
        from html.parser import HTMLParser
    except ImportError:
        raise ImportError("ebooklib is required for EPUB parsing")

    class HTMLTextExtractor(HTMLParser):
        """Extract text from HTML content."""

        def __init__(self):
            super().__init__()
            self.text_parts = []

        def handle_data(self, data):
            self.text_parts.append(data)

        def get_text(self):
            return " ".join(self.text_parts)

    book = epub.read_epub(file_path)

    # Extract metadata
    title = book.get_metadata("DC", "title")
    title = title[0][0] if title else "Untitled"

    author = book.get_metadata("DC", "creator")
    author = author[0][0] if author else None

    # Extract chapters
    chapters = []
    all_text_parts = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode("utf-8", errors="ignore")

        # Extract text from HTML
        parser = HTMLTextExtractor()
        parser.feed(content)
        text = parser.get_text().strip()

        if text:
            # Try to get chapter title from content (before normalization)
            chapter_title = (
                _extract_chapter_title(text) or f"Chapter {len(chapters) + 1}"
            )
            
            # Normalize text to remove hard line breaks
            text = _normalize_line_breaks(text)
            
            chapters.append((chapter_title, text))
            all_text_parts.append(text)

    return ParsedDocument(
        title=title,
        author=author,
        raw_text="\n\n".join(all_text_parts),
        chapters=chapters,
        format="epub",
    )


def parse_pdf(file_path: str) -> ParsedDocument:
    """Parse a PDF file."""
    try:
        import pymupdf
    except ImportError:
        raise ImportError("pymupdf is required for PDF parsing")

    doc = pymupdf.open(file_path)

    # Extract metadata
    metadata = doc.metadata
    title = metadata.get("title") or os.path.splitext(os.path.basename(file_path))[0]
    author = metadata.get("author")

    # Extract text from all pages
    all_text = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            all_text.append(text)

    doc.close()

    full_text = "\n\n".join(all_text)
    chapters = _split_into_chapters(full_text)

    # Normalize each chapter's content to remove single line breaks
    normalized_chapters = []
    for ch_title, ch_content in chapters:
        normalized_chapters.append((ch_title, _normalize_line_breaks(ch_content)))

    # Reconstruct normalized raw text
    normalized_full_text = "\n\n".join([f"{t}\n\n{c}" for t, c in normalized_chapters])

    return ParsedDocument(
        title=title,
        author=author,
        raw_text=normalized_full_text,
        chapters=normalized_chapters,
        format="pdf",
    )


def parse_file(file_path: str) -> ParsedDocument:
    """Parse a file based on its format."""
    format_type = detect_format(file_path)

    parsers = {
        "txt": parse_txt,
        "md": parse_markdown,
        "epub": parse_epub,
        "pdf": parse_pdf,
    }

    parser = parsers.get(format_type)
    if not parser:
        raise ValueError(f"Unsupported format: {format_type}")

    return parser(file_path)


def _split_into_chapters(text: str) -> List[Tuple[str, str]]:
    """Split text into chapters based on common patterns."""
    # Common chapter patterns
    chapter_patterns = [
        r"(?:^|\n\n)(Chapter\s+\d+[^\n]*)\n",
        r"(?:^|\n\n)(CHAPTER\s+\d+[^\n]*)\n",
        r"(?:^|\n\n)(Part\s+\d+[^\n]*)\n",
        r"(?:^|\n\n)(PART\s+\d+[^\n]*)\n",
        r"(?:^|\n\n)(\d+\.\s+[^\n]+)\n",
    ]

    chapters = []

    for pattern in chapter_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if matches:
            for i, match in enumerate(matches):
                title = match.group(1).strip()
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                if content:
                    chapters.append((title, content))
            break

    # If no chapters found, treat entire text as one chapter
    if not chapters:
        chapters = [("Chapter 1", text)]

    return chapters


def _split_markdown_chapters(content: str) -> List[Tuple[str, str]]:
    """Split markdown by headings."""
    # Split by h1 or h2
    pattern = r"(?:^|\n)(#{1,2}\s+[^\n]+)\n"
    matches = list(re.finditer(pattern, content))

    chapters = []

    if matches:
        for i, match in enumerate(matches):
            title = match.group(1).strip().lstrip("#").strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start:end].strip()
            if section_content:
                chapters.append((title, _markdown_to_text(section_content)))
    else:
        chapters = [("Content", _markdown_to_text(content))]

    return chapters


def _normalize_line_breaks(text: str) -> str:
    """
    Remove single line breaks and replace them with a space,
    but preserve double line breaks (paragraphs).
    """
    if not text:
        return ""

    # Normalize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split by double or more newlines (paragraph boundaries)
    # This regex matches two or more newlines, possibly with spaces in between
    paragraphs = re.split(r"\n\s*\n+", text)

    normalized_paragraphs = []
    for p in paragraphs:
        # Replace single newlines with spaces
        p_clean = p.replace("\n", " ")
        # Squeeze multiple spaces into one
        p_clean = re.sub(r"\s+", " ", p_clean).strip()
        if p_clean:
            normalized_paragraphs.append(p_clean)

    return "\n\n".join(normalized_paragraphs)


def _markdown_to_text(md: str) -> str:
    """Convert markdown to plain text."""
    text = md
    # Remove headers (keep text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    # Remove links, keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # Remove code blocks
    text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Normalize line breaks (remove single line breaks, keep double)
    text = _normalize_line_breaks(text)

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_chapter_title(text: str) -> Optional[str]:
    """Try to extract a chapter title from text content."""
    lines = text.strip().split("\n")[:5]  # Check first 5 lines

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Check for chapter-like patterns
        if re.match(r"^(Chapter|CHAPTER|Part|PART)\s+", line):
            return line[:100]  # Limit length
        if len(line) < 60 and line[0].isupper():
            # Short line starting with capital might be a title
            return line

    return None
