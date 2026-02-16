"""
@fileoverview SimplyNarrated - File Parser, Extract and normalize text from various file formats
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
import shutil
import logging
import zipfile
import html as html_module
from typing import Tuple, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MIN_CHAPTER_WORDS = 500


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


def parse_zip(file_path: str) -> ParsedDocument:
    """Parse a Gutenberg-style ZIP containing HTML and optional cover image."""
    MAX_ZIP_MEMBERS = 200
    MAX_UNCOMPRESSED = 100 * 1024 * 1024  # 100 MB safety limit

    try:
        zf = zipfile.ZipFile(file_path)
    except (zipfile.BadZipFile, Exception) as e:
        raise ValueError(f"Invalid or corrupt ZIP file: {e}")

    members = zf.infolist()
    if len(members) > MAX_ZIP_MEMBERS:
        zf.close()
        raise ValueError(f"ZIP has too many members ({len(members)})")

    total_uncompressed = sum(m.file_size for m in members if not m.is_dir())
    if total_uncompressed > MAX_UNCOMPRESSED:
        zf.close()
        raise ValueError("ZIP uncompressed content exceeds size limit")

    # Find the largest HTML file
    html_members = [
        m for m in members
        if not m.is_dir()
        and m.filename.lower().endswith((".html", ".htm"))
        and not m.filename.startswith(("__MACOSX/", "."))
        and _safe_zip_member(m.filename)
    ]

    if not html_members:
        zf.close()
        raise ValueError("ZIP does not contain any HTML files")

    largest_html = max(html_members, key=lambda m: m.file_size)

    raw_html = zf.read(largest_html.filename)
    zf.close()

    # Decode HTML
    html_text = raw_html.decode("utf-8", errors="ignore")

    # Extract title from <title> tag
    title_match = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    title = "Untitled"
    if title_match:
        title = html_module.unescape(title_match.group(1).strip())
        # Strip common Gutenberg suffixes like " | Project Gutenberg"
        title = re.sub(r"\s*\|\s*Project\s+Gutenberg\b.*$", "", title, flags=re.IGNORECASE).strip()

    # Strip Gutenberg header/footer boilerplate
    body_html = _strip_gutenberg_boilerplate(html_text)

    # Convert HTML to plain text
    plain_text = _html_to_text(body_html)

    # Split into chapters
    chapters = _split_into_chapters(plain_text)

    # Normalize each chapter
    normalized_chapters = []
    for ch_title, ch_content in chapters:
        normalized_chapters.append((ch_title, _normalize_line_breaks(ch_content)))

    full_text = "\n\n".join([f"{t}\n\n{c}" for t, c in normalized_chapters])

    return ParsedDocument(
        title=title,
        author=None,
        raw_text=full_text,
        chapters=normalized_chapters,
        format="zip",
    )


def _safe_zip_member(name: str) -> bool:
    """Check that a ZIP member path is safe (no path traversal)."""
    if name.startswith("/") or ".." in name.split("/"):
        return False
    return True


def _strip_gutenberg_boilerplate(html_text: str) -> str:
    """Remove Project Gutenberg header and footer sections from HTML."""
    # Remove everything inside <section id="pg-header">...</section>
    html_text = re.sub(
        r'<(?:div|section)[^>]*id=["\']pg-header["\'][^>]*>.*?</(?:div|section)>',
        "", html_text, flags=re.DOTALL | re.IGNORECASE,
    )
    # Remove everything inside <section id="pg-footer">...</section>
    html_text = re.sub(
        r'<(?:div|section)[^>]*id=["\']pg-footer["\'][^>]*>.*?</(?:div|section)>',
        "", html_text, flags=re.DOTALL | re.IGNORECASE,
    )
    return html_text


def _html_to_text(html_text: str) -> str:
    """Convert HTML to readable plain text for audiobook narration."""
    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove <head>...</head>
    text = re.sub(r"<head[^>]*>.*?</head>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove image tags
    text = re.sub(r"<img[^>]*>", "", text, flags=re.IGNORECASE)

    # Convert <br> and <br/> to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Convert block-level closing tags to double newlines
    block_tags = r"</(?:p|div|h[1-6]|li|blockquote|tr|section|article|header|footer|pre)>"
    text = re.sub(block_tags, "\n\n", text, flags=re.IGNORECASE)

    # Convert <hr> to double newline
    text = re.sub(r"<hr[^>]*>", "\n\n", text, flags=re.IGNORECASE)

    # Remove all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html_module.unescape(text)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def parse_file(file_path: str) -> ParsedDocument:
    """Parse a file based on its format."""
    format_type = detect_format(file_path)

    parsers = {
        "txt": parse_txt,
        "md": parse_markdown,
        "pdf": parse_pdf,
        "zip": parse_zip,
    }

    parser = parsers.get(format_type)
    if not parser:
        raise ValueError(f"Unsupported format: {format_type}")

    return parser(file_path)


def extract_cover_image(file_path: str, output_dir: str) -> Optional[str]:
    """
    Attempt to extract a cover image from the source file.

    For PDF: extracts the first image from page 1.
    For Markdown: locates the first local image reference.
    For TXT: no cover extraction.

    Returns the filename of the saved cover image (e.g. 'cover.jpg'), or None.
    """
    format_type = detect_format(file_path)

    if format_type == "pdf":
        return _extract_cover_from_pdf(file_path, output_dir)
    elif format_type == "md":
        return _extract_cover_from_markdown(file_path, output_dir)
    elif format_type == "zip":
        return _extract_cover_from_zip(file_path, output_dir)
    return None


def _extract_cover_from_pdf(file_path: str, output_dir: str) -> Optional[str]:
    """Extract the first image from page 1 of a PDF as the cover."""
    try:
        import pymupdf
    except ImportError:
        return None

    try:
        doc = pymupdf.open(file_path)
        if len(doc) == 0:
            doc.close()
            return None

        # Get images from the first page
        page = doc[0]
        images = page.get_images(full=True)

        if not images:
            doc.close()
            return None

        # Use the first image
        xref = images[0][0]
        base_image = doc.extract_image(xref)
        doc.close()

        if not base_image or not base_image.get("image"):
            return None

        # Determine extension from the image format
        img_ext = base_image.get("ext", "png").lower()
        if img_ext in ("jpg", "jpeg"):
            cover_filename = "cover.jpg"
        elif img_ext == "png":
            cover_filename = "cover.png"
        else:
            # Convert unknown formats to png extension
            cover_filename = "cover.png"

        cover_path = os.path.join(output_dir, cover_filename)
        with open(cover_path, "wb") as f:
            f.write(base_image["image"])

        logger.info("Extracted cover image from PDF: %s", cover_filename)
        return cover_filename

    except Exception as e:
        logger.warning("Failed to extract cover from PDF: %s", e)
        return None


def _extract_cover_from_markdown(file_path: str, output_dir: str) -> Optional[str]:
    """Find the first local image reference in a markdown file and copy it as cover."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Find the first markdown image reference: ![alt](path)
        match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", content)
        if not match:
            return None

        img_ref = match.group(1).strip()

        # Only handle local file paths — skip URLs to avoid SSRF
        if img_ref.startswith(("http://", "https://", "ftp://", "data:", "//")):
            return None

        # Resolve relative to the source file's directory
        source_dir = os.path.dirname(os.path.abspath(file_path))
        img_path = os.path.normpath(os.path.join(source_dir, img_ref))

        # Security: ensure the resolved path is within or near the source directory
        if not os.path.isfile(img_path):
            return None

        # Determine cover filename from the image extension
        ext = os.path.splitext(img_path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            cover_filename = "cover.jpg"
        elif ext == ".png":
            cover_filename = "cover.png"
        else:
            return None

        cover_path = os.path.join(output_dir, cover_filename)
        shutil.copy2(img_path, cover_path)

        logger.info("Copied cover image from markdown reference: %s", cover_filename)
        return cover_filename

    except Exception as e:
        logger.warning("Failed to extract cover from markdown: %s", e)
        return None


def _extract_cover_from_zip(file_path: str, output_dir: str) -> Optional[str]:
    """Extract a cover image from a ZIP archive.

    Looks for an image file whose name contains 'cover' (case-insensitive).
    """
    try:
        with zipfile.ZipFile(file_path) as zf:
            image_members = [
                m for m in zf.infolist()
                if not m.is_dir()
                and _safe_zip_member(m.filename)
                and m.filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]

            # Find the member whose basename contains 'cover'
            cover_member = None
            for m in image_members:
                basename = os.path.basename(m.filename).lower()
                if "cover" in basename:
                    cover_member = m
                    break

            if not cover_member:
                return None

            # Determine output extension
            ext = os.path.splitext(cover_member.filename)[1].lower()
            if ext in (".jpg", ".jpeg"):
                cover_filename = "cover.jpg"
            elif ext == ".png":
                cover_filename = "cover.png"
            else:
                cover_filename = "cover.png"

            cover_data = zf.read(cover_member.filename)
            cover_path = os.path.join(output_dir, cover_filename)
            with open(cover_path, "wb") as f:
                f.write(cover_data)

            logger.info("Extracted cover image from ZIP: %s", cover_filename)
            return cover_filename

    except Exception as e:
        logger.warning("Failed to extract cover from ZIP: %s", e)
        return None


def _count_words(text: str) -> int:
    """Count words in text using simple token boundaries."""
    return len(re.findall(r"\b\w+\b", text or ""))


def _merge_short_chapters(
    chapters: List[Tuple[str, str]],
    min_words: int = MIN_CHAPTER_WORDS,
) -> List[Tuple[str, str]]:
    """Merge adjacent chapters until each chapter reaches the minimum size."""
    if not chapters:
        return chapters

    merged: List[Tuple[str, str]] = []
    current_title, current_content = chapters[0]
    current_content = (current_content or "").strip()

    for title, content in chapters[1:]:
        content = (content or "").strip()
        if _count_words(current_content) < min_words:
            if current_title == "Preamble":
                current_title = title
            current_content = f"{current_content}\n\n{content}".strip()
        else:
            merged.append((current_title, current_content))
            current_title, current_content = title, content

    merged.append((current_title, current_content))

    if len(merged) > 1 and _count_words(merged[-1][1]) < min_words:
        prev_title, prev_content = merged[-2]
        last_title, last_content = merged[-1]
        combined = f"{prev_content}\n\n{last_title}\n\n{last_content}".strip()
        merged[-2] = (prev_title, combined)
        merged.pop()

    return merged


def _split_into_chapters(text: str) -> List[Tuple[str, str]]:
    """Split text into chapters based on common patterns."""
    # Common chapter patterns, tried in priority order
    chapter_patterns = [
        r"(?:^|\n\n)(Chapter\s+\d+[^\n]*)\n",
        r"(?:^|\n\n)(CHAPTER\s+\d+[^\n]*)\n",
        r"(?:^|\n\n)(Part\s+\d+[^\n]*)\n",
        r"(?:^|\n\n)(PART\s+\d+[^\n]*)\n",
        # ALL-CAPS section headers surrounded by blank lines (e.g. essay titles)
        r"\n\n\n+([A-Z][A-Z][A-Z \-'.,;:!?]+)\n",
        r"(?:^|\n\n)(\d+\.\s+[^\n]+)\n",
    ]

    chapters = []

    for pattern in chapter_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if not matches:
            continue

        # Heuristic: if the numbered-list pattern's first match is far into
        # the document, it's likely matching numbered paragraphs rather than
        # chapter headings — skip it.
        if pattern == r"(?:^|\n\n)(\d+\.\s+[^\n]+)\n":
            if matches[0].start() / max(len(text), 1) > 0.3:
                continue

        # Capture any text before the first match as a preamble chapter
        preamble = text[: matches[0].start()].strip()
        if preamble:
            chapters.append(("Preamble", preamble))

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

    return _merge_short_chapters(chapters)


def _split_markdown_chapters(content: str) -> List[Tuple[str, str]]:
    """Split markdown by headings."""
    # Split by h1 or h2
    pattern = r"(?:^|\n)(#{1,2}\s+[^\n]+)\n"
    matches = list(re.finditer(pattern, content))

    chapters = []

    if matches:
        # Capture any text before the first heading as a preamble
        preamble = content[: matches[0].start()].strip()
        if preamble:
            chapters.append(("Preamble", _markdown_to_text(preamble)))

        for i, match in enumerate(matches):
            title = match.group(1).strip().lstrip("#").strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start:end].strip()
            if section_content:
                chapters.append((title, _markdown_to_text(section_content)))
    else:
        chapters = [("Content", _markdown_to_text(content))]

    return _merge_short_chapters(chapters)


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
    # Remove images (before links so ![alt](…) isn't partially matched)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # Remove links, keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove code blocks
    text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Normalize line breaks (remove single line breaks, keep double)
    text = _normalize_line_breaks(text)

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
