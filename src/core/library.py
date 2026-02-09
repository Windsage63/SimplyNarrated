"""
@fileoverview BookTalk - Library Manager, File-based persistence for audiobook library using JSON metadata files
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
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

from src.models.schemas import BookInfo, ChapterInfo


@dataclass
class BookMetadata:
    """Book metadata stored in metadata.json"""

    id: str
    title: str
    author: Optional[str] = None
    source_file: Optional[str] = None
    original_filename: Optional[str] = None
    voice: Optional[str] = None
    total_chapters: int = 0
    total_duration: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    chapters: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Bookmark:
    """User playback position"""

    chapter: int
    position: float  # seconds
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class LibraryManager:
    """Manages the audiobook library using file-based storage."""

    def __init__(self, library_dir: str):
        self.library_dir = library_dir
        os.makedirs(library_dir, exist_ok=True)

    def get_book_dir(self, book_id: str) -> str:
        """Get the directory path for a book."""
        return os.path.join(self.library_dir, book_id)

    def scan_library(self) -> List[BookInfo]:
        """Scan library directory and return all books with metadata."""
        books = []

        if not os.path.exists(self.library_dir):
            return books

        for book_id in os.listdir(self.library_dir):
            book_dir = self.get_book_dir(book_id)
            metadata_path = os.path.join(book_dir, "metadata.json")

            if os.path.isdir(book_dir) and os.path.exists(metadata_path):
                try:
                    book = self.get_book(book_id)
                    if book:
                        books.append(book)
                except Exception as e:
                    print(f"Error loading book {book_id}: {e}")

        # Sort by created_at descending (newest first)
        books.sort(key=lambda b: b.created_at, reverse=True)
        return books

    def get_book(self, book_id: str) -> Optional[BookInfo]:
        """Load book metadata from JSON file."""
        metadata_path = os.path.join(self.get_book_dir(book_id), "metadata.json")

        if not os.path.exists(metadata_path):
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse chapters
            chapters = []
            for ch in data.get("chapters", []):
                chapters.append(
                    ChapterInfo(
                        number=ch.get("number", 0),
                        title=ch.get("title", f"Chapter {ch.get('number', 0)}"),
                        duration=ch.get("duration"),
                        audio_path=ch.get("audio_path"),
                        completed=ch.get("completed", False),
                    )
                )

            return BookInfo(
                id=book_id,
                title=data.get("title", "Unknown Title"),
                author=data.get("author"),
                cover_url=data.get("cover_url"),
                original_filename=data.get("original_filename"),
                total_chapters=data.get("total_chapters", len(chapters)),
                total_duration=data.get("total_duration"),
                created_at=datetime.fromisoformat(
                    data.get("created_at", datetime.now().isoformat())
                ),
                chapters=chapters,
            )
        except Exception as e:
            print(f"Error reading metadata for {book_id}: {e}")
            return None

    def save_book(self, book_id: str, metadata: BookMetadata) -> bool:
        """Save book metadata to JSON file."""
        book_dir = self.get_book_dir(book_id)
        os.makedirs(book_dir, exist_ok=True)

        metadata_path = os.path.join(book_dir, "metadata.json")

        try:
            data = asdict(metadata)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving metadata for {book_id}: {e}")
            return False

    def update_book_metadata(self, book_id: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in book metadata."""
        metadata_path = os.path.join(self.get_book_dir(book_id), "metadata.json")

        if not os.path.exists(metadata_path):
            return False

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data.update(updates)

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error updating metadata for {book_id}: {e}")
            return False

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
            print(f"Error reading bookmark for {book_id}: {e}")
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
            print(f"Error saving bookmark for {book_id}: {e}")
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
                    print(f"Error deleting book {book_id}: {e}")
                    return False
                # Wait before retrying
                time.sleep(retry_delay)
        
        return False

    def count_in_progress(self, active_jobs: Dict[str, Any]) -> int:
        """Count how many jobs are currently in progress."""
        from src.models.schemas import JobStatus

        count = 0
        for job in active_jobs.values():
            if hasattr(job, "status") and job.status == JobStatus.PROCESSING:
                count += 1
        return count


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
