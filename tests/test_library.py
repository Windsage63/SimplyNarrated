"""
Tests for the LibraryManager (file-based persistence).
"""

import os
import json
import zipfile
import pytest
from datetime import datetime

from src.core.library import LibraryManager, BookMetadata, Bookmark
from src.core.portability import export_book_archive, import_book_archive


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


class TestPortability:
    def test_export_and_import_round_trip(self, library_manager, tmp_path):
        book_id = "12345678-1234-1234-1234-123456789abc"
        meta = BookMetadata(
            id=book_id,
            title="Portable Book",
            author="Portable Author",
            source_file="source.txt",
            original_filename="portable.txt",
            total_chapters=1,
            chapters=[
                {
                    "number": 1,
                    "title": "Ch 1",
                    "audio_path": "chapter_01.mp3",
                    "text_path": "chapter_01.txt",
                    "completed": True,
                }
            ],
        )
        assert library_manager.save_book(book_id, meta) is True

        book_dir = library_manager.get_book_dir(book_id)
        with open(os.path.join(book_dir, "chapter_01.mp3"), "wb") as f:
            f.write(b"fake-mp3-data")
        with open(os.path.join(book_dir, "chapter_01.txt"), "w", encoding="utf-8") as f:
            f.write("Portable chapter text")
        with open(os.path.join(book_dir, "source.txt"), "w", encoding="utf-8") as f:
            f.write("Portable source")
        with open(os.path.join(book_dir, "bookmarks.json"), "w", encoding="utf-8") as f:
            json.dump({"chapter": 1, "position": 42.0}, f)
        with open(os.path.join(book_dir, "cover.png"), "wb") as f:
            f.write(b"png")

        archive_path, download_name = export_book_archive(library_manager, book_id)
        assert download_name == "Portable Book.zip"
        assert os.path.exists(archive_path)

        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            assert any(name.endswith("/export_manifest.json") for name in names)
            assert any(name.endswith("/chapter_01.mp3") for name in names)
            assert any(name.endswith("/chapter_01.txt") for name in names)

        library_manager.delete_book(book_id)

        result = import_book_archive(library_manager, archive_path)
        assert result["status"] == "imported"
        imported_dir = library_manager.get_book_dir(result["book_id"])
        assert os.path.exists(os.path.join(imported_dir, "chapter_01.mp3"))
        assert os.path.exists(os.path.join(imported_dir, "chapter_01.txt"))
        assert os.path.exists(os.path.join(imported_dir, "bookmarks.json"))

    def test_import_remaps_conflicting_book_id(self, library_manager):
        book_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        existing = BookMetadata(id=book_id, title="Existing")
        library_manager.save_book(book_id, existing)

        archive_root = os.path.join(library_manager.library_dir, "archive-source")
        os.makedirs(archive_root, exist_ok=True)
        archive_path = os.path.join(archive_root, "conflict.zip")
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(
                "Portable/export_manifest.json",
                json.dumps({"archive_type": "simplynarrated-audiobook", "schema_version": 1}),
            )
            archive.writestr(
                "Portable/metadata.json",
                json.dumps(
                    {
                        "id": book_id,
                        "title": "Imported",
                        "total_chapters": 1,
                        "chapters": [
                            {
                                "number": 1,
                                "title": "Chapter 1",
                                "audio_path": "chapter_01.mp3",
                                "text_path": "chapter_01.txt",
                                "completed": True,
                            }
                        ],
                    }
                ),
            )
            archive.writestr("Portable/chapter_01.mp3", b"audio")
            archive.writestr("Portable/chapter_01.txt", "text")

        result = import_book_archive(library_manager, archive_path)
        assert result["id_remapped"] is True
        assert result["book_id"] != book_id
