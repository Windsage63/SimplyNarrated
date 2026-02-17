"""
Integration tests for PATCH /api/book/{id} and POST /api/book/{id}/cover.

These tests exercise the route handlers to verify fast-path selection,
ffmpeg fallback, and error responses.
"""

import os
import shutil
import uuid
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.core.library import init_library_manager
from src.core.job_manager import init_job_manager
from src.core.cleanup_manager import init_cleanup_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def setup_app(tmp_path):
    """Initialize app managers with temp directories."""
    lib_dir = str(tmp_path / "library")
    data_dir = str(tmp_path / "data")
    os.makedirs(lib_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "uploads"), exist_ok=True)

    init_library_manager(lib_dir)
    init_job_manager(data_dir)
    init_cleanup_manager(data_dir)
    return lib_dir


@pytest.fixture
def client(setup_app):
    """Synchronous FastAPI TestClient."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def seeded_book(setup_app, small_m4a_copy, sample_cover):
    """
    Seed the library with a book directory containing an M4A, cover, and
    transcript.  Returns the book_id.
    """
    lib_dir = setup_app
    book_id = str(uuid.uuid4())
    book_dir = os.path.join(lib_dir, book_id)
    os.makedirs(book_dir, exist_ok=True)

    shutil.copy2(small_m4a_copy, os.path.join(book_dir, "audiobook.m4a"))
    shutil.copy2(sample_cover, os.path.join(book_dir, "cover.jpg"))

    with open(os.path.join(book_dir, "transcript.txt"), "w") as f:
        f.write("Test transcript content.")

    return book_id


# ---------------------------------------------------------------------------
# Test 1 — PATCH title returns fast  (Scenario 1)
# ---------------------------------------------------------------------------
def test_patch_title_returns_fast(client, seeded_book):
    resp = client.patch(
        f"/api/book/{seeded_book}",
        json={"title": "Patched Title"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Patched Title"
    assert body["method"] == "fast"


# ---------------------------------------------------------------------------
# Test 2 — PATCH author returns fast  (Scenario 2)
# ---------------------------------------------------------------------------
def test_patch_author_returns_fast(client, seeded_book):
    resp = client.patch(
        f"/api/book/{seeded_book}",
        json={"author": "Patched Author"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["author"] == "Patched Author"
    assert body["method"] == "fast"


# ---------------------------------------------------------------------------
# Test 3 — PATCH title + author  (Scenario 3)
# ---------------------------------------------------------------------------
def test_patch_title_and_author(client, seeded_book):
    resp = client.patch(
        f"/api/book/{seeded_book}",
        json={"title": "Both", "author": "Fields"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Both"
    assert body["author"] == "Fields"
    assert body["method"] == "fast"


# ---------------------------------------------------------------------------
# Test 4 — Upload cover returns fast  (Scenario 4)
# ---------------------------------------------------------------------------
def test_upload_cover_returns_fast(client, seeded_book, sample_cover):
    with open(sample_cover, "rb") as f:
        resp = client.post(
            f"/api/book/{seeded_book}/cover",
            files={"file": ("cover.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "cover_url" in body
    assert body["method"] == "fast"


# ---------------------------------------------------------------------------
# Test 5 — PATCH then GET persists  (Scenario 7)
# ---------------------------------------------------------------------------
def test_patch_then_get_persists(client, seeded_book):
    client.patch(
        f"/api/book/{seeded_book}",
        json={"title": "Persistent Title", "author": "Persistent Author"},
    )

    resp = client.get(f"/api/book/{seeded_book}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Persistent Title"
    assert body["author"] == "Persistent Author"


# ---------------------------------------------------------------------------
# Test 6 — SNMETA survives patch  (Scenario 8)
# ---------------------------------------------------------------------------
def test_snmeta_survives_patch(client, seeded_book):
    client.patch(
        f"/api/book/{seeded_book}",
        json={"title": "SNMETA Survivor"},
    )

    resp = client.get(f"/api/book/{seeded_book}")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("id") is not None
    assert body.get("created_at") is not None
    assert body.get("original_filename") is not None


# ---------------------------------------------------------------------------
# Test 7 — Fallback to ffmpeg  (Scenario 9)
# ---------------------------------------------------------------------------
def test_fallback_to_ffmpeg(client, seeded_book):
    with patch(
        "src.api.routes.update_m4a_metadata_fast",
        side_effect=RuntimeError("simulated failure"),
    ):
        resp = client.patch(
            f"/api/book/{seeded_book}",
            json={"title": "Fallback Title"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "full_rewrite"
    assert body["title"] == "Fallback Title"


# ---------------------------------------------------------------------------
# Test 8 — Both paths fail → 423  (Scenario 10)
# ---------------------------------------------------------------------------
def test_save_error_returns_423(client, seeded_book):
    with (
        patch(
            "src.api.routes.update_m4a_metadata_fast",
            side_effect=RuntimeError("fast fail"),
        ),
        patch(
            "src.api.routes.update_m4a_metadata",
            side_effect=PermissionError("locked"),
        ),
    ):
        resp = client.patch(
            f"/api/book/{seeded_book}",
            json={"title": "Error Title"},
        )

    assert resp.status_code == 423
    assert "Failed to save metadata" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 9 — Empty body returns 400  (Scenario 11)
# ---------------------------------------------------------------------------
def test_no_fields_returns_400(client, seeded_book):
    resp = client.patch(
        f"/api/book/{seeded_book}",
        json={},
    )
    assert resp.status_code == 400
    assert "No fields to update" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 10 — Invalid book ID returns 404
# ---------------------------------------------------------------------------
def test_invalid_book_id_returns_404(client):
    fake_id = str(uuid.uuid4())
    resp = client.patch(
        f"/api/book/{fake_id}",
        json={"title": "Nope"},
    )
    assert resp.status_code == 404
