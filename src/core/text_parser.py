from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.core.parser_artifacts import write_parser_artifacts


@dataclass(frozen=True)
class ParsedTextChapter:
    """Speech-ready chapter produced directly from a TXT parser."""

    number: int
    title: str
    content: str


@dataclass(frozen=True)
class ParsedTextDocument:
    """TXT document prepared for the downstream speech pipeline."""

    title: str
    author: Optional[str]
    format: str
    chapters: List[ParsedTextChapter]
    cover_filename: Optional[str] = None


def parse_text_document(
    file_path: str,
    output_dir: Optional[str] = None,
    max_words_per_chapter: int = 4000,
) -> ParsedTextDocument:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as source_file:
        raw_text = source_file.read()

    normalized_text = _normalize_text(raw_text)
    blocks = _build_blocks(normalized_text)
    title, author, body_blocks, title_source = _extract_title_and_author(blocks, file_path)
    chapters, parse_report = _build_chapters(body_blocks, max_words_per_chapter=max_words_per_chapter)

    if output_dir:
        cleaned_text = _render_cleaned_text(title, author, body_blocks)
        report_payload = {
            "title": title,
            "title_source": title_source,
            "author": author,
            "chapter_count": len(chapters),
            "chapter_titles": [chapter.title for chapter in chapters],
            "explicit_chapter_markers": parse_report["explicit_chapter_markers"],
            "fallback_split_used": parse_report["fallback_split_used"],
            "warnings": parse_report["warnings"],
        }
        write_parser_artifacts(output_dir, cleaned_text, report_payload)

    return ParsedTextDocument(
        title=title,
        author=author,
        format="txt",
        chapters=chapters,
    )


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.lstrip("\ufeff")
    normalized = normalized.replace("\t", " ")
    normalized = re.sub(r"[ \u00a0]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _build_blocks(text: str) -> List[str]:
    raw_blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    blocks: List[str] = []

    for raw_block in raw_blocks:
        lines = [line.strip() for line in raw_block.split("\n") if line.strip()]
        if not lines:
            continue
        if len(lines) == 1 or _looks_like_heading(lines[0]):
            blocks.append(lines[0])
            continue
        if _should_reflow(lines):
            blocks.append(" ".join(lines))
        else:
            blocks.append("\n".join(lines))

    return blocks


def _extract_title_and_author(blocks: List[str], file_path: str) -> Tuple[str, Optional[str], List[str], str]:
    fallback_title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").strip() or "Untitled"
    if not blocks:
        return fallback_title, None, [], "filename"

    title_source = "filename"
    title = fallback_title
    author = None
    start_index = 0

    first_block = blocks[0]
    if len(first_block) <= 120 and not _looks_like_heading(first_block):
        title = first_block
        title_source = "first_block"
        start_index = 1

    if start_index < len(blocks):
        possible_author = blocks[start_index]
        author_match = re.match(r"^by\s+(.+)$", possible_author, re.IGNORECASE)
        if author_match and len(possible_author) <= 120:
            author = author_match.group(1).strip()
            start_index += 1

    return title, author, blocks[start_index:], title_source


def _build_chapters(blocks: List[str], max_words_per_chapter: int) -> Tuple[List[ParsedTextChapter], Dict[str, object]]:
    warnings: List[str] = []
    chapter_markers = [block for block in blocks if _looks_like_heading(block)]
    explicit_markers = len(chapter_markers)

    if explicit_markers:
        chapters = _build_explicit_chapters(blocks)
        if not chapters:
            warnings.append("Explicit chapter markers were found but no chapter content was produced.")
    else:
        chapters = _split_blocks_by_word_budget(blocks, max_words_per_chapter)
        warnings.append("No explicit chapter markers found; fallback word-budget splitting used.")

    return chapters, {
        "explicit_chapter_markers": explicit_markers,
        "fallback_split_used": explicit_markers == 0,
        "warnings": warnings,
    }


def _build_explicit_chapters(blocks: List[str]) -> List[ParsedTextChapter]:
    chapters: List[ParsedTextChapter] = []
    current_title: Optional[str] = None
    current_blocks: List[str] = []
    pending_front_matter: List[str] = []

    for block in blocks:
        if _looks_like_heading(block):
            if current_title is not None:
                content = _join_chapter_blocks(current_blocks)
                if content:
                    chapters.append(
                        ParsedTextChapter(
                            number=len(chapters) + 1,
                            title=current_title,
                            content=content,
                        )
                    )
            elif pending_front_matter:
                front_matter_content = _join_chapter_blocks(pending_front_matter)
                if front_matter_content:
                    chapters.append(
                        ParsedTextChapter(
                            number=len(chapters) + 1,
                            title="Opening",
                            content=front_matter_content,
                        )
                    )
                pending_front_matter = []

            current_title = block
            current_blocks = []
            continue

        if current_title is None:
            pending_front_matter.append(block)
        else:
            current_blocks.append(block)

    if current_title is not None:
        content = _join_chapter_blocks(current_blocks)
        if content:
            chapters.append(
                ParsedTextChapter(
                    number=len(chapters) + 1,
                    title=current_title,
                    content=content,
                )
            )
    elif pending_front_matter:
        content = _join_chapter_blocks(pending_front_matter)
        if content:
            chapters.append(ParsedTextChapter(number=1, title="Chapter 1", content=content))

    return chapters


def _split_blocks_by_word_budget(blocks: List[str], max_words_per_chapter: int) -> List[ParsedTextChapter]:
    chapters: List[ParsedTextChapter] = []
    current_blocks: List[str] = []
    current_words = 0

    for block in blocks:
        block_words = len(block.split())
        if current_blocks and current_words + block_words > max_words_per_chapter:
            chapters.append(
                ParsedTextChapter(
                    number=len(chapters) + 1,
                    title=f"Chapter {len(chapters) + 1}",
                    content=_join_chapter_blocks(current_blocks),
                )
            )
            current_blocks = []
            current_words = 0

        current_blocks.append(block)
        current_words += block_words

    if current_blocks:
        chapters.append(
            ParsedTextChapter(
                number=len(chapters) + 1,
                title=f"Chapter {len(chapters) + 1}",
                content=_join_chapter_blocks(current_blocks),
            )
        )

    return chapters or [ParsedTextChapter(number=1, title="Chapter 1", content="")]


def _join_chapter_blocks(blocks: List[str]) -> str:
    return "\n\n".join(block for block in blocks if block).strip()


def _render_cleaned_text(title: str, author: Optional[str], body_blocks: List[str]) -> str:
    output_blocks = [title]
    if author:
        output_blocks.append(f"By {author}")
    output_blocks.extend(body_blocks)
    return _join_chapter_blocks(output_blocks) + "\n"


def _should_reflow(lines: List[str]) -> bool:
    if len(lines) <= 1:
        return False
    average_length = sum(len(line) for line in lines) / len(lines)
    if average_length >= 45:
        return True
    continuation_pairs = sum(
        1
        for left, right in zip(lines, lines[1:])
        if right and (right[0].islower() or not re.search(r"[.!?][\"'”’)]?$", left))
    )
    return continuation_pairs >= 1


def _looks_like_heading(value: str) -> bool:
    stripped = value.strip()
    case_insensitive_patterns = (
        r"^(chapter|part|book)\s+([0-9]+|[ivxlcdm]+)\b.*$",
        r"^\d+\.\s+.+$",
    )
    if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in case_insensitive_patterns):
        return True
    return bool(re.match(r"^[A-Z][A-Z0-9 ,;:'\-?!]{2,120}$", stripped))