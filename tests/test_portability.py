"""
Unit tests for src/core/portability.py helpers.
"""

import json
import os
import uuid
import zipfile
from datetime import datetime

import pytest

from src.core.portability import (
    sanitize_filename_component,
    export_book_archive,
    import_book_archive,
    ARCHIVE_MANIFEST_NAME,
)

import src.core.library as lib_module


# ---------------------------------------------------------------------------
# sanitize_filename_component
# ---------------------------------------------------------------------------


class TestSanitizeFilenameComponent:
    def test_removes_illegal_characters(self):
        result = sanitize_filename_component('My <Book>: "Title"')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result

    def test_empty_string_returns_default(self):
        result = sanitize_filename_component("")
        assert result == "audiobook"

    def test_windows_reserved_names_renamed(self):
        result = sanitize_filename_component("CON")
        assert result.upper() != "CON"

    def test_none_returns_default(self):
        result = sanitize_filename_component(None)
        assert result == "audiobook"

    def test_normal_title_unchanged(self):
        result = sanitize_filename_component("My Normal Book Title")
        assert result == "My Normal Book Title"

    def test_strips_leading_trailing_dots_spaces(self):
        result = sanitize_filename_component("  ..Title..  ")
        assert not result.startswith(".")
        assert not result.endswith(".")
        assert not result.startswith(" ")


# ---------------------------------------------------------------------------
# Export / Import roundtrip
# ---------------------------------------------------------------------------


@pytest.fixture
def populated_library(tmp_library_dir):
    """Create a library with a complete book ready for export."""
    book_id = str(uuid.uuid4())
    book_dir = tmp_library_dir / book_id
    book_dir.mkdir()

    metadata = {
        "id": book_id,
        "title": "Export Test Book",
        "author": "Test Author",
        "source_file": "source.txt",
        "original_filename": "export_test.txt",
        "voice": "af_heart",
        "total_chapters": 1,
        "total_duration": "0:05",
        "created_at": datetime.now().isoformat(),
        "format": "mp3",
        "quality": "sd",
        "chapters": [
            {
                "number": 1,
                "title": "Chapter 1",
                "duration": "0:05",
                "audio_path": "chapter_01.mp3",
                "text_path": "chapter_01.txt",
                "completed": True,
            }
        ],
    }

    (book_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (book_dir / "chapter_01.mp3").write_bytes(b"fake mp3 data")
    (book_dir / "chapter_01.txt").write_text("Chapter one text.", encoding="utf-8")
    (book_dir / "source.txt").write_text("Source text.", encoding="utf-8")

    manager = lib_module.init_library_manager(str(tmp_library_dir))
    yield manager, book_id

    lib_module._library_manager = None


class TestExportImportRoundtrip:
    def test_export_creates_zip(self, populated_library):
        manager, book_id = populated_library
        archive_path, filename = export_book_archive(manager, book_id)

        assert os.path.exists(archive_path)
        assert filename.endswith(".zip")

        with zipfile.ZipFile(archive_path) as zf:
            names = zf.namelist()
            # Check that manifest and metadata exist (they are prefixed with book title)
            assert any(ARCHIVE_MANIFEST_NAME in n for n in names)
            assert any("metadata.json" in n for n in names)

        os.remove(archive_path)

    def test_export_missing_book_raises(self, populated_library):
        manager, _ = populated_library
        with pytest.raises(FileNotFoundError):
            export_book_archive(manager, "00000000-0000-0000-0000-000000000000")

    def test_import_restores_metadata(self, populated_library):
        manager, book_id = populated_library
        archive_path, _ = export_book_archive(manager, book_id)

        result = import_book_archive(manager, archive_path)

        assert result["status"] == "imported"
        assert result["title"] == "Export Test Book"
        assert result["total_chapters"] == 1

        os.remove(archive_path)
