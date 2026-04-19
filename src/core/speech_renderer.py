"""
@fileoverview SimplyNarrated - Speech renderer, Convert Docling chunks into plain text for TTS
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

import re
from typing import Iterable, List

from src.core.docling_adapter import ImportedChapter
from src.core.encoder import format_duration

WORDS_PER_MINUTE = 150


def render_chapter_text(chapter: ImportedChapter) -> str:
    """Render a Docling-backed chapter to plain UTF-8 narration text."""
    blocks: List[str] = [_clean_inline_markdown(chapter.title)]
    last_relative_headings: List[str] = []

    for chunk in chapter.chunks:
        relative_headings = _relative_headings(chunk.headings, chapter.title)
        shared_prefix = _shared_prefix_length(last_relative_headings, relative_headings)

        for heading in relative_headings[shared_prefix:]:
            cleaned_heading = _clean_inline_markdown(heading)
            if cleaned_heading:
                blocks.append(cleaned_heading)

        last_relative_headings = relative_headings

        cleaned_text = normalize_speech_text(chunk.text)
        if cleaned_text:
            blocks.append(cleaned_text)

    return _join_blocks(blocks)


def normalize_speech_text(text: str) -> str:
    """Normalize Docling chunk text for narration while preserving paragraphs."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", normalized)
    normalized = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", normalized)
    normalized = re.sub(r"^\s{0,3}#{1,6}\s+", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"^\s*[-*+]\s+", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"^\s*\d+\.\s+", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"`{1,3}", "", normalized)
    normalized = normalized.replace("**", "").replace("__", "")
    normalized = normalized.replace("*", "").replace("_", "")

    lines = [line.strip() for line in normalized.split("\n")]
    collapsed: List[str] = []
    previous_blank = False

    for line in lines:
        if line:
            collapsed.append(line)
            previous_blank = False
        elif not previous_blank:
            collapsed.append("")
            previous_blank = True

    return "\n".join(collapsed).strip()


def count_words(text: str) -> int:
    """Count words in rendered text."""
    return len(text.split())


def estimate_duration_seconds(text: str, speed: float = 1.0) -> float:
    """Estimate speech duration using a simple words-per-minute model."""
    words = count_words(text)
    if words == 0 or speed <= 0:
        return 0.0
    minutes = words / WORDS_PER_MINUTE
    return (minutes * 60.0) / speed


def format_total_duration(texts: Iterable[str], speed: float = 1.0) -> str:
    """Format total estimated duration for multiple rendered chapter texts."""
    total_seconds = sum(estimate_duration_seconds(text, speed=speed) for text in texts)
    return format_duration(total_seconds)


def _relative_headings(headings: List[str], chapter_title: str) -> List[str]:
    cleaned = [_clean_inline_markdown(heading) for heading in headings if heading and heading.strip()]
    chapter_title_clean = _clean_inline_markdown(chapter_title)

    if chapter_title_clean in cleaned:
        index = cleaned.index(chapter_title_clean)
        return cleaned[index + 1 :]

    return cleaned


def _shared_prefix_length(left: List[str], right: List[str]) -> int:
    count = 0
    for left_value, right_value in zip(left, right):
        if left_value != right_value:
            break
        count += 1
    return count


def _clean_inline_markdown(text: str) -> str:
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    cleaned = cleaned.replace("**", "").replace("__", "")
    cleaned = cleaned.replace("*", "").replace("_", "")
    cleaned = cleaned.replace("`", "")
    return cleaned.strip()


def _join_blocks(blocks: List[str]) -> str:
    return "\n\n".join(block for block in blocks if block).strip()