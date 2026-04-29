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