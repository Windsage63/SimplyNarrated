import json

from tests.conftest import create_library_book


def test_upload_rejects_markdown_files(app_client):
    client, _data_dir, _library_dir = app_client

    response = client.post(
        "/api/upload",
        files={"file": ("sample.md", b"# Heading\n\nBody", "text/markdown")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
    assert ".md" not in response.json()["detail"]


def test_upload_accepts_text_files(app_client):
    client, _data_dir, _library_dir = app_client

    response = client.post(
        "/api/upload",
        files={"file": ("sample.txt", b"Chapter 1\n\nBody text", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "sample.txt"
    assert payload["chapters_detected"] >= 1


def test_upload_still_accepts_pdf_files(app_client):
    client, _data_dir, _library_dir = app_client

    response = client.post(
        "/api/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "sample.pdf"


def test_cover_upload_rejects_invalid_image_bytes(app_client):
    client, _data_dir, library_dir = app_client
    book_id, _book_dir, _metadata = create_library_book(library_dir)

    response = client.post(
        f"/api/book/{book_id}/cover",
        files={"file": ("cover.jpg", b"not-an-image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid image file. Only JPG and PNG images are allowed."


def test_cover_upload_uses_detected_image_type_over_client_mime(app_client):
    client, _data_dir, library_dir = app_client
    book_id, book_dir, _metadata = create_library_book(library_dir)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
    )

    response = client.post(
        f"/api/book/{book_id}/cover",
        files={"file": ("cover.jpg", png_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json()["cover_url"] == f"/api/book/{book_id}/cover"
    assert (book_dir / "cover.png").read_bytes() == png_bytes
    assert not (book_dir / "cover.jpg").exists()

    metadata = json.loads((book_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["cover_url"] == f"/api/book/{book_id}/cover"