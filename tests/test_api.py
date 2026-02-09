"""
Tests for the REST API endpoints.

Tests marked @pytest.mark.slow require the real Kokoro TTS model.
"""

import os
import io
import json
import asyncio
import pytest
import numpy as np

import src.core.job_manager as jm_module
import src.core.library as lib_module
import src.core.tts_engine as tts_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_upload_file(content: bytes, filename: str):
    """Build the multipart dict for httpx file upload."""
    return {"file": (filename, io.BytesIO(content), "application/octet-stream")}


def _populate_book(library_dir: str, book_id: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"):
    """Create a book in the library dir with metadata and a tiny WAV chapter."""
    from scipy.io import wavfile
    from datetime import datetime

    book_dir = os.path.join(library_dir, book_id)
    os.makedirs(book_dir, exist_ok=True)

    metadata = {
        "id": book_id,
        "title": "API Test Book",
        "author": "Tester",
        "total_chapters": 1,
        "total_duration": "0m",
        "created_at": datetime.now().isoformat(),
        "format": "wav",
        "quality": "sd",
        "chapters": [
            {
                "number": 1,
                "title": "Chapter 1",
                "duration": "0:02",
                "audio_path": "chapter_01.wav",
                "completed": True,
            }
        ],
    }
    with open(os.path.join(book_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f)

    sr = 24000
    t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    wavfile.write(os.path.join(book_dir, "chapter_01.wav"), sr, tone)

    return book_id


# ===========================================================================
# Health & static
# ===========================================================================


class TestHealthEndpoint:
    async def test_health(self, app_client):
        resp = await app_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


# ===========================================================================
# Upload
# ===========================================================================


class TestUploadEndpoint:
    async def test_upload_txt(self, app_client):
        content = b"Hello world. This is a test file."
        resp = await app_client.post(
            "/api/upload",
            files=_make_upload_file(content, "test.txt"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["filename"] == "test.txt"
        assert data["file_size"] == len(content)

    async def test_upload_md(self, app_client):
        resp = await app_client.post(
            "/api/upload",
            files=_make_upload_file(b"# Title\n\nText", "doc.md"),
        )
        assert resp.status_code == 200

    async def test_upload_unsupported(self, app_client):
        resp = await app_client.post(
            "/api/upload",
            files=_make_upload_file(b"data", "file.docx"),
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    async def test_upload_too_large(self, app_client):
        # 51 MB of zeros
        big = b"\x00" * (51 * 1024 * 1024)
        resp = await app_client.post(
            "/api/upload",
            files=_make_upload_file(big, "huge.txt"),
        )
        assert resp.status_code == 413


# ===========================================================================
# Voices
# ===========================================================================


class TestVoicesEndpoint:
    async def test_list_voices(self, app_client):
        resp = await app_client.get("/api/voices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 28
        assert len(data["voices"]) == 28
        # Spot-check a voice
        ids = [v["id"] for v in data["voices"]]
        assert "af_heart" in ids


# ===========================================================================
# Status
# ===========================================================================


class TestStatusEndpoint:
    async def test_pending_status(self, app_client):
        # Upload a file first
        upload = await app_client.post(
            "/api/upload",
            files=_make_upload_file(b"Some text.", "s.txt"),
        )
        job_id = upload.json()["job_id"]

        resp = await app_client.get(f"/api/status/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["progress"] == 0.0

    async def test_status_not_found(self, app_client):
        resp = await app_client.get("/api/status/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ===========================================================================
# Generate (full TTS pipeline — slow)
# ===========================================================================


@pytest.mark.slow
class TestGenerateEndpoint:
    async def test_full_conversion(self, app_client, tmp_data_dir):
        """Upload → generate → poll until complete → verify output."""
        # Upload a short text
        text = (
            "Chapter 1\n"
            "The quick brown fox jumps over the lazy dog. This is a test.\n\n"
            "Chapter 2\n"
            "Pack my box with five dozen liquor jugs."
        )
        upload_resp = await app_client.post(
            "/api/upload",
            files=_make_upload_file(text.encode(), "short.txt"),
        )
        assert upload_resp.status_code == 200
        job_id = upload_resp.json()["job_id"]

        # Start generation
        gen_resp = await app_client.post(
            "/api/generate",
            json={
                "job_id": job_id,
                "narrator_voice": "af_heart",
                "speed": 1.0,
                "quality": "sd",
                "format": "wav",
            },
        )
        assert gen_resp.status_code == 200

        # Poll status until completed or timeout (120s max)
        for _ in range(240):
            await asyncio.sleep(0.5)
            status_resp = await app_client.get(f"/api/status/{job_id}")
            status = status_resp.json()["status"]
            if status in ("completed", "failed"):
                break

        assert status == "completed", f"Job ended with status: {status}"

        # Verify output directory has audio files
        library_dir = str(tmp_data_dir / "library")
        output_dir = os.path.join(library_dir, job_id)
        assert os.path.exists(output_dir)
        assert os.path.exists(os.path.join(output_dir, "metadata.json"))

        # Should have at least one chapter audio file
        audio_files = [f for f in os.listdir(output_dir) if f.startswith("chapter_")]
        assert len(audio_files) >= 1


@pytest.mark.slow
class TestCancelEndpoint:
    async def test_cancel_running_job(self, app_client):
        """Start a conversion and immediately cancel it."""
        # Upload larger text to ensure it's still running when we cancel
        text = ("Some text to convert. " * 500)
        upload = await app_client.post(
            "/api/upload",
            files=_make_upload_file(text.encode(), "cancel_test.txt"),
        )
        job_id = upload.json()["job_id"]

        await app_client.post(
            "/api/generate",
            json={"job_id": job_id, "quality": "sd", "format": "wav"},
        )

        # Give it a moment to start, then cancel
        await asyncio.sleep(1.0)
        cancel_resp = await app_client.post(f"/api/cancel/{job_id}")
        assert cancel_resp.status_code == 200

        # Check status settled
        await asyncio.sleep(0.5)
        status_resp = await app_client.get(f"/api/status/{job_id}")
        assert status_resp.json()["status"] in ("cancelled", "completed")


# ===========================================================================
# Library
# ===========================================================================


class TestLibraryEndpoint:
    async def test_empty_library(self, app_client):
        resp = await app_client.get("/api/library")
        assert resp.status_code == 200
        data = resp.json()
        assert data["books"] == []
        assert data["total"] == 0

    async def test_library_with_book(self, app_client, tmp_library_dir):
        book_id = _populate_book(str(tmp_library_dir))
        resp = await app_client.get("/api/library")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["books"][0]["id"] == book_id


# ===========================================================================
# Book details
# ===========================================================================


class TestBookEndpoint:
    async def test_get_book(self, app_client, tmp_library_dir):
        book_id = _populate_book(str(tmp_library_dir))
        resp = await app_client.get(f"/api/book/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "API Test Book"
        assert data["total_chapters"] == 1

    async def test_book_not_found(self, app_client):
        resp = await app_client.get("/api/book/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ===========================================================================
# Audio streaming
# ===========================================================================


class TestAudioEndpoint:
    async def test_stream_wav(self, app_client, tmp_library_dir):
        book_id = _populate_book(str(tmp_library_dir))
        resp = await app_client.get(f"/api/audio/{book_id}/1")
        assert resp.status_code == 200
        assert resp.headers["content-type"] in ("audio/wav", "audio/x-wav")
        assert len(resp.content) > 0

    async def test_audio_not_found(self, app_client, tmp_library_dir):
        book_id = _populate_book(str(tmp_library_dir))
        resp = await app_client.get(f"/api/audio/{book_id}/99")
        assert resp.status_code == 404

    async def test_invalid_book_id(self, app_client):
        resp = await app_client.get("/api/audio/not-a-valid-uuid/1")
        assert resp.status_code == 400


# ===========================================================================
# Bookmarks
# ===========================================================================


class TestBookmarkEndpoints:
    async def test_save_and_load(self, app_client, tmp_library_dir):
        book_id = _populate_book(str(tmp_library_dir))

        # Save
        resp = await app_client.post(
            f"/api/bookmark?book_id={book_id}&chapter=2&position=33.5"
        )
        assert resp.status_code == 200

        # Load
        resp = await app_client.get(f"/api/bookmark/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["chapter"] == 2
        assert data["position"] == pytest.approx(33.5)

    async def test_default_bookmark(self, app_client, tmp_library_dir):
        book_id = _populate_book(str(tmp_library_dir))
        resp = await app_client.get(f"/api/bookmark/{book_id}")
        data = resp.json()
        assert data["chapter"] == 1
        assert data["position"] == 0.0


# ===========================================================================
# Delete
# ===========================================================================


class TestDeleteEndpoint:
    async def test_delete_book(self, app_client, tmp_library_dir):
        book_id = _populate_book(str(tmp_library_dir))
        book_dir = os.path.join(str(tmp_library_dir), book_id)
        assert os.path.exists(book_dir)

        resp = await app_client.delete(f"/api/book/{book_id}")
        assert resp.status_code == 200
        assert not os.path.exists(book_dir)

    async def test_delete_not_found(self, app_client):
        resp = await app_client.delete("/api/book/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_delete_invalid_id(self, app_client):
        resp = await app_client.delete("/api/book/not-a-valid-uuid")
        assert resp.status_code == 400
