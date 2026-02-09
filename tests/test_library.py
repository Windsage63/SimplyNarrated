"""
Tests for the LibraryManager (file-based persistence).
"""

import os
import json
import pytest
from datetime import datetime

from src.core.library import LibraryManager, BookMetadata, Bookmark


# ---------------------------------------------------------------------------
# scan / save / get
# ---------------------------------------------------------------------------


class TestScanLibrary:
    def test_empty_library(self, library_manager):
        books = library_manager.scan_library()
        assert books == []

    def test_finds_books(self, library_manager):
        # Create two books
        for i in range(2):
            meta = BookMetadata(
                id=f"book-{i}",
                title=f"Book {i}",
                total_chapters=1,
                chapters=[{"number": 1, "title": "Ch1", "completed": True}],
            )
            library_manager.save_book(meta.id, meta)

        books = library_manager.scan_library()
        assert len(books) == 2

    def test_sorted_newest_first(self, library_manager):
        m1 = BookMetadata(id="old", title="Old", created_at="2025-01-01T00:00:00")
        m2 = BookMetadata(id="new", title="New", created_at="2026-06-01T00:00:00")
        library_manager.save_book(m1.id, m1)
        library_manager.save_book(m2.id, m2)

        books = library_manager.scan_library()
        assert books[0].title == "New"


class TestSaveAndGetBook:
    def test_round_trip(self, library_manager):
        meta = BookMetadata(
            id="abc-123",
            title="Test Book",
            author="Author",
            total_chapters=2,
            chapters=[
                {"number": 1, "title": "Ch 1", "completed": True},
                {"number": 2, "title": "Ch 2", "completed": False},
            ],
        )
        assert library_manager.save_book(meta.id, meta) is True

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
    def test_updates_field(self, library_manager):
        meta = BookMetadata(id="upd", title="Original")
        library_manager.save_book(meta.id, meta)
        library_manager.update_book_metadata("upd", {"title": "Updated"})

        book = library_manager.get_book("upd")
        assert book.title == "Updated"

    def test_update_nonexistent(self, library_manager):
        assert library_manager.update_book_metadata("nope", {"title": "x"}) is False


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------


class TestBookmarks:
    def test_save_and_get(self, library_manager):
        # Need a book directory to exist first
        meta = BookMetadata(id="bm-test", title="BM Book")
        library_manager.save_book(meta.id, meta)

        assert library_manager.save_bookmark("bm-test", chapter=3, position=42.5) is True

        bm = library_manager.get_bookmark("bm-test")
        assert bm is not None
        assert bm.chapter == 3
        assert bm.position == pytest.approx(42.5)

    def test_get_missing_bookmark(self, library_manager):
        meta = BookMetadata(id="no-bm", title="No Bookmark")
        library_manager.save_book(meta.id, meta)
        assert library_manager.get_bookmark("no-bm") is None

    def test_bookmark_no_book_dir(self, library_manager):
        assert library_manager.save_bookmark("ghost", chapter=1, position=0) is False


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDeleteBook:
    def test_deletes_directory(self, library_manager):
        meta = BookMetadata(id="del-me", title="Delete Me")
        library_manager.save_book(meta.id, meta)
        book_dir = library_manager.get_book_dir("del-me")
        assert os.path.exists(book_dir)

        assert library_manager.delete_book("del-me") is True
        assert not os.path.exists(book_dir)

    def test_delete_nonexistent(self, library_manager):
        assert library_manager.delete_book("nope") is False
