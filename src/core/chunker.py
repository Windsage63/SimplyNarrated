"""
@fileoverview BookTalk - Text Chunker, Split text into manageable chunks for TTS processing
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

import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a chunk of text for TTS processing."""

    index: int
    title: str
    content: str
    word_count: int
    estimated_duration: float  # in seconds


# Maximum words per chunk
MAX_WORDS_PER_CHUNK = 4000

# Approximate words per minute for speech
WORDS_PER_MINUTE = 150


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def estimate_duration(word_count: int, speed: float = 1.0) -> float:
    """Estimate audio duration in seconds."""
    minutes = word_count / WORDS_PER_MINUTE
    return (minutes * 60) / speed


def chunk_text(
    text: str, max_words: int = MAX_WORDS_PER_CHUNK, chapter_title: str = "Chapter"
) -> List[TextChunk]:
    """
    Split text into chunks of max_words or less.
    Tries to split at natural boundaries (paragraphs, sentences).
    """
    words = text.split()
    total_words = len(words)

    if total_words <= max_words:
        return [
            TextChunk(
                index=0,
                title=chapter_title,
                content=text,
                word_count=total_words,
                estimated_duration=estimate_duration(total_words),
            )
        ]

    chunks = []
    current_pos = 0
    chunk_index = 0

    while current_pos < len(words):
        # Get next chunk of words
        chunk_words = words[current_pos : current_pos + max_words]
        chunk_text = " ".join(chunk_words)

        # If we're not at the end, try to find a good break point
        if current_pos + max_words < len(words):
            chunk_text = _find_break_point(chunk_text)
            actual_words = len(chunk_text.split())
        else:
            actual_words = len(chunk_words)

        if chunk_text.strip():
            chunks.append(
                TextChunk(
                    index=chunk_index,
                    title=f"{chapter_title} (Part {chunk_index + 1})"
                    if len(chunks) > 0 or current_pos + actual_words < len(words)
                    else chapter_title,
                    content=chunk_text.strip(),
                    word_count=actual_words,
                    estimated_duration=estimate_duration(actual_words),
                )
            )
            chunk_index += 1

        current_pos += actual_words

    return chunks


def _find_break_point(text: str) -> str:
    """
    Find a natural break point in the text (end of paragraph or sentence).
    Returns text up to the break point.
    """
    # Try to find paragraph break (double newline)
    para_match = text.rfind("\n\n")
    if para_match > len(text) * 0.7:  # Only if it's in the last 30%
        return text[:para_match]

    # Try to find sentence ending
    sentence_patterns = [
        r'[.!?]["\']\s+',  # End of dialogue
        r"[.!?]\s+",  # Regular sentence end
    ]

    for pattern in sentence_patterns:
        matches = list(re.finditer(pattern, text))
        if matches:
            # Find the last match that's at least 70% through
            for match in reversed(matches):
                if match.end() > len(text) * 0.7:
                    return text[: match.end()]

    # Fallback: return as-is
    return text


def chunk_chapters(
    chapters: List[Tuple[str, str]], max_words: int = MAX_WORDS_PER_CHUNK
) -> List[TextChunk]:
    """
    Chunk a list of chapters, keeping chapter boundaries where possible.
    """
    all_chunks = []
    chunk_counter = 0

    for title, content in chapters:
        chapter_chunks = chunk_text(content, max_words, title)

        # Update indices for global numbering
        for chunk in chapter_chunks:
            chunk.index = chunk_counter
            all_chunks.append(chunk)
            chunk_counter += 1

    return all_chunks


def get_total_duration(chunks: List[TextChunk]) -> str:
    """Get total estimated duration as a formatted string."""
    total_seconds = sum(chunk.estimated_duration for chunk in chunks)
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_total_words(chunks: List[TextChunk]) -> int:
    """Get total word count across all chunks."""
    return sum(chunk.word_count for chunk in chunks)
