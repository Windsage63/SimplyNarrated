import struct
import zlib
import json

import fitz
import pytest
from fastapi.testclient import TestClient

import src.main as main_module


def _png_chunk(chunk_type, data):
    return (
        struct.pack("!I", len(data))
        + chunk_type
        + data
        + struct.pack("!I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def _png_1x1_bytes():
    ihdr = struct.pack("!2I5B", 1, 1, 8, 2, 0, 0, 0)
    raw_scanline = b"\x00\xff\x00\x00"
    idat = zlib.compress(raw_scanline)
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def create_pdf(path, *, author=None, title="Sample PDF", include_cover=False):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), title)
    page.insert_text((72, 100), "Chapter 1")
    page.insert_text((72, 130), "This is a sample paragraph for PDF flow testing.")

    if include_cover:
        image_rect = fitz.Rect(72, 150, 144, 222)
        page.insert_image(image_rect, stream=_png_1x1_bytes())

    metadata = {"title": title}
    if author is not None:
        metadata["author"] = author
    document.set_metadata(metadata)
    document.save(path)
    document.close()
    return path


@pytest.fixture
def pdf_factory(tmp_path):
    def _create(name="sample.pdf", *, author=None, title="Sample PDF", include_cover=False):
        path = tmp_path / name
        create_pdf(
            path,
            author=author,
            title=title,
            include_cover=include_cover,
        )
        return path

    return _create


def create_library_book(
    library_dir,
    *,
    book_id="11111111-1111-1111-1111-111111111111",
    title="Test Book",
    author="Test Author",
    chapter_text="Original chapter text.",
    voice="af_heart",
    quality="sd",
    fmt="mp3",
):
    book_dir = library_dir / book_id
    book_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": book_id,
        "title": title,
        "author": author,
        "cover_url": None,
        "source_file": "source.pdf",
        "original_filename": "source.pdf",
        "voice": voice,
        "total_chapters": 1,
        "total_duration": "0:00",
        "created_at": "2026-04-28T00:00:00",
        "format": fmt,
        "quality": quality,
        "chapters": [
            {
                "number": 1,
                "title": "Chapter 1",
                "duration": "0:00",
                "audio_path": "chapter_01.mp3",
                "text_path": "chapter_01.txt",
                "completed": True,
            }
        ],
    }

    (book_dir / "chapter_01.txt").write_text(chapter_text, encoding="utf-8")
    (book_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return book_id, book_dir, metadata


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    library_dir = data_dir / "library"
    uploads_dir = data_dir / "uploads"
    library_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(main_module, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(main_module, "LIBRARY_DIR", str(library_dir))

    with TestClient(main_module.app) as client:
        yield client, data_dir, library_dir