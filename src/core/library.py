"""
@fileoverview SimplyNarrated - Library Manager, file-based library with embedded M4A metadata as source of truth
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
import json
import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field, asdict

from src.models.schemas import BookInfo, ChapterInfo
from src.core.encoder import read_m4a_metadata

logger = logging.getLogger(__name__)


@dataclass
class Bookmark:
    """User playback position"""

    chapter: int
    position: float  # seconds
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class LibraryManager:
    """Manages the audiobook library using embedded M4A metadata."""

    def __init__(self, library_dir: str):
        self.library_dir = library_dir
        os.makedirs(library_dir, exist_ok=True)

    def get_book_dir(self, book_id: str) -> str:
        """Get the directory path for a book."""
        return os.path.join(self.library_dir, book_id)

    def get_book_audio_path(self, book_id: str) -> Optional[str]:
        """Return the primary M4A file path for a book."""
        book_dir = self.get_book_dir(book_id)
        if not os.path.isdir(book_dir):
            return None

        candidates = []
        for name in os.listdir(book_dir):
            lower = name.lower()
            if not lower.endswith(".m4a"):
                continue
            if ".metadata." in lower or ".tmp." in lower or lower.endswith(".tmp.m4a"):
                continue
            candidates.append(name)
        if not candidates:
            return None

        candidates.sort(key=lambda name: os.path.getmtime(os.path.join(book_dir, name)), reverse=True)
        return os.path.join(book_dir, candidates[0])

    def scan_library(self) -> List[BookInfo]:
        """Scan library directory and return all books with embedded metadata."""
        books = []

        if not os.path.exists(self.library_dir):
            return books

        for book_id in os.listdir(self.library_dir):
            book_dir = self.get_book_dir(book_id)
            if os.path.isdir(book_dir):
                try:
                    book = self.get_book(book_id)
                    if book:
                        books.append(book)
                except Exception as e:
                    logger.warning("Error loading book %s: %s", book_id, e)

        # Sort by created_at descending (newest first)
        books.sort(key=lambda b: b.created_at, reverse=True)
        return books

    def get_book(self, book_id: str) -> Optional[BookInfo]:
        """Load book metadata from embedded M4A tags."""
        book_dir = self.get_book_dir(book_id)
        audio_path = self.get_book_audio_path(book_id)

        if not audio_path:
            return None

        try:
            data = read_m4a_metadata(audio_path)

            # Parse chapters
            chapters = []
            for ch in data.get("chapters", []):
                chapters.append(
                    ChapterInfo(
                        number=ch.get("number", 0),
                        title=ch.get("title", f"Chapter {ch.get('number', 0)}"),
                        duration=ch.get("duration"),
                        start_seconds=ch.get("start_seconds"),
                        end_seconds=ch.get("end_seconds"),
                        transcript_start=ch.get("transcript_start"),
                        transcript_end=ch.get("transcript_end"),
                        completed=ch.get("completed", False),
                    )
                )

            cover_path = None
            for candidate in ("cover.jpg", "cover.png"):
                candidate_path = os.path.join(book_dir, candidate)
                if os.path.exists(candidate_path) and os.path.getsize(candidate_path) > 0:
                    cover_path = candidate
                    break

            created_at_str = data.get("created_at")
            created_at = (
                datetime.fromisoformat(created_at_str)
                if created_at_str
                else datetime.fromtimestamp(os.path.getmtime(audio_path))
            )

            return BookInfo(
                id=book_id,
                title=data.get("title", "Unknown Title"),
                author=data.get("author"),
                cover_url=f"/api/book/{book_id}/cover" if cover_path else None,
                original_filename=data.get("original_filename"),
                total_chapters=len(chapters),
                total_duration=data.get("total_duration"),
                created_at=created_at,
                book_file=os.path.basename(audio_path),
                transcript_path=data.get("transcript_path") or "transcript.txt",
                chapters=chapters,
            )
        except Exception as e:
            logger.warning("Error reading embedded metadata for %s: %s", book_id, e)
            return None

    def get_bookmark(self, book_id: str) -> Optional[Bookmark]:
        """Get the user's playback position for a book."""
        bookmark_path = os.path.join(self.get_book_dir(book_id), "bookmarks.json")

        if not os.path.exists(bookmark_path):
            return None

        try:
            with open(bookmark_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Bookmark(
                chapter=data.get("chapter", 1),
                position=data.get("position", 0.0),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
            )
        except Exception as e:
            logger.warning("Error reading bookmark for %s: %s", book_id, e)
            return None

    def save_bookmark(self, book_id: str, chapter: int, position: float) -> bool:
        """Save a playback bookmark for a book."""
        book_dir = self.get_book_dir(book_id)

        if not os.path.exists(book_dir):
            return False

        bookmark_path = os.path.join(book_dir, "bookmarks.json")

        try:
            bookmark = Bookmark(chapter=chapter, position=position)
            with open(bookmark_path, "w", encoding="utf-8") as f:
                json.dump(asdict(bookmark), f, indent=2)
            return True
        except Exception as e:
            logger.error("Error saving bookmark for %s: %s", book_id, e)
            return False

    def delete_book(self, book_id: str) -> bool:
        """Delete a book and all its files."""
        import shutil
        import time

        book_dir = self.get_book_dir(book_id)

        if not os.path.exists(book_dir):
            return False

        # Try to delete multiple times (helps on Windows if files are temporarily locked)
        max_retries = 3
        retry_delay = 0.5  # seconds

        for i in range(max_retries):
            try:
                shutil.rmtree(book_dir)
                return True
            except Exception as e:
                # If it's the last attempt, log the error
                if i == max_retries - 1:
                    logger.error("Error deleting book %s: %s", book_id, e)
                    return False
                # Wait before retrying
                time.sleep(retry_delay)
        
        return False

# Global library manager instance
_library_manager: Optional[LibraryManager] = None


def get_library_manager() -> LibraryManager:
    """Get the global library manager instance."""
    global _library_manager
    if _library_manager is None:
        raise RuntimeError("LibraryManager not initialized")
    return _library_manager


def init_library_manager(library_dir: str) -> LibraryManager:
    """Initialize the global library manager."""
    global _library_manager
    _library_manager = LibraryManager(library_dir)
    return _library_manager
