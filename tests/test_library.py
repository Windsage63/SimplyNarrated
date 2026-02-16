"""
Tests for the LibraryManager (file-based persistence).
"""

import os
import pytest
from src.core.library import LibraryManager


def _create_dummy_m4a(book_dir: str, file_name: str = "book.m4a") -> str:
    os.makedirs(book_dir, exist_ok=True)
    path = os.path.join(book_dir, file_name)
    with open(path, "wb") as f:
        f.write(b"dummy")
    return path


# ---------------------------------------------------------------------------
# scan / save / get
# ---------------------------------------------------------------------------


class TestScanLibrary:
    def test_empty_library(self, library_manager):
        books = library_manager.scan_library()
        assert books == []

    def test_finds_books(self, library_manager, monkeypatch):
        for i in range(2):
            _create_dummy_m4a(library_manager.get_book_dir(f"book-{i}"), "audio.m4a")

        def fake_reader(_path):
            return {
                "title": "Book",
                "author": "Author",
                "chapters": [{"number": 1, "title": "Ch1", "completed": True}],
                "total_duration": "0:01",
                "created_at": "2026-01-01T00:00:00",
                "transcript_path": "transcript.txt",
                "original_filename": "book.txt",
            }

        monkeypatch.setattr("src.core.library.read_m4a_metadata", fake_reader)

        books = library_manager.scan_library()
        assert len(books) == 2

    def test_sorted_newest_first(self, library_manager, monkeypatch):
        _create_dummy_m4a(library_manager.get_book_dir("old"), "old.m4a")
        _create_dummy_m4a(library_manager.get_book_dir("new"), "new.m4a")

        def fake_reader(path):
            if "old" in path:
                return {
                    "title": "Old",
                    "author": "A",
                    "chapters": [],
                    "total_duration": "0:01",
                    "created_at": "2025-01-01T00:00:00",
                    "transcript_path": "transcript.txt",
                }
            return {
                "title": "New",
                "author": "A",
                "chapters": [],
                "total_duration": "0:01",
                "created_at": "2026-06-01T00:00:00",
                "transcript_path": "transcript.txt",
            }

        monkeypatch.setattr("src.core.library.read_m4a_metadata", fake_reader)

        books = library_manager.scan_library()
        assert books[0].title == "New"


class TestSaveAndGetBook:
    def test_get_book_from_embedded_metadata(self, library_manager, monkeypatch):
        _create_dummy_m4a(library_manager.get_book_dir("abc-123"), "book.m4a")

        monkeypatch.setattr(
            "src.core.library.read_m4a_metadata",
            lambda _path: {
                "title": "Test Book",
                "author": "Author",
                "chapters": [
                    {"number": 1, "title": "Ch 1", "completed": True},
                    {"number": 2, "title": "Ch 2", "completed": False},
                ],
                "total_duration": "0:05",
                "created_at": "2026-01-01T00:00:00",
                "transcript_path": "transcript.txt",
                "original_filename": "src.txt",
            },
        )

        book = library_manager.get_book("abc-123")
        assert book is not None
        assert book.title == "Test Book"
        assert book.author == "Author"
        assert book.total_chapters == 2
        assert len(book.chapters) == 2
        assert book.chapters[0].title == "Ch 1"

    def test_get_nonexistent(self, library_manager):
        assert library_manager.get_book("no-such-id") is None


class TestUpdateMetadata:
    def test_updates_field(self, library_manager, monkeypatch):
        _create_dummy_m4a(library_manager.get_book_dir("upd"), "book.m4a")

        monkeypatch.setattr(
            "src.core.library.read_m4a_metadata",
            lambda _path: {
                "title": "Original",
                "author": "Author",
                "chapters": [{"number": 1, "title": "Ch 1", "completed": True}],
                "total_duration": "0:01",
                "created_at": "2026-01-01T00:00:00",
                "transcript_path": "transcript.txt",
                "original_filename": "src.txt",
            },
        )

        captured = {}

        def fake_update(**kwargs):
            captured.update(kwargs)
            return kwargs["file_path"]

        monkeypatch.setattr("src.core.library.update_m4a_metadata", fake_update)

        assert library_manager.update_book_metadata("upd", {"title": "Updated"}) is True
        assert captured["title"] == "Updated"

    def test_update_nonexistent(self, library_manager):
        assert library_manager.update_book_metadata("nope", {"title": "x"}) is False


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------


class TestBookmarks:
    def test_save_and_get(self, library_manager):
        # Need a book directory to exist first
        _create_dummy_m4a(library_manager.get_book_dir("bm-test"), "book.m4a")

        assert library_manager.save_bookmark("bm-test", chapter=3, position=42.5) is True

        bm = library_manager.get_bookmark("bm-test")
        assert bm is not None
        assert bm.chapter == 3
        assert bm.position == pytest.approx(42.5)

    def test_get_missing_bookmark(self, library_manager):
        _create_dummy_m4a(library_manager.get_book_dir("no-bm"), "book.m4a")
        assert library_manager.get_bookmark("no-bm") is None

    def test_bookmark_no_book_dir(self, library_manager):
        assert library_manager.save_bookmark("ghost", chapter=1, position=0) is False


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDeleteBook:
    def test_deletes_directory(self, library_manager):
        _create_dummy_m4a(library_manager.get_book_dir("del-me"), "book.m4a")
        book_dir = library_manager.get_book_dir("del-me")
        assert os.path.exists(book_dir)

        assert library_manager.delete_book("del-me") is True
        assert not os.path.exists(book_dir)

    def test_delete_nonexistent(self, library_manager):
        assert library_manager.delete_book("nope") is False
