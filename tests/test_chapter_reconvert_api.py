from src.core.job_manager import get_job_manager

from tests.conftest import create_library_book


def test_update_chapter_text_endpoint_persists_changes(app_client):
    client, _data_dir, library_dir = app_client
    book_id, book_dir, _metadata = create_library_book(library_dir, chapter_text="Original text")

    response = client.put(
        f"/api/book/{book_id}/chapter/1/text",
        json={"content": "Edited chapter text for reconvert."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    assert (book_dir / "chapter_01.txt").read_text(encoding="utf-8") == "Edited chapter text for reconvert."


def test_reconvert_chapter_endpoint_queues_job_with_frontend_expected_config(app_client, monkeypatch):
    client, _data_dir, library_dir = app_client
    book_id, book_dir, _metadata = create_library_book(library_dir, chapter_text="Ready for reconvert")
    job_manager = get_job_manager()
    captured = {}

    async def fake_start_job(job_id, config, process_func):
        captured["job_id"] = job_id
        captured["config"] = config
        captured["process_name"] = process_func.__name__
        return True

    monkeypatch.setattr(job_manager, "start_job", fake_start_job)

    response = client.post(
        f"/api/book/{book_id}/chapter/1/reconvert",
        json={
            "narrator_voice": "af_heart",
            "speed": 1.1,
            "quality": "sd",
            "format": "mp3",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert captured["process_name"] == "process_chapter_reconvert_job"
    assert captured["config"]["book_id"] == book_id
    assert captured["config"]["chapter_number"] == 1
    assert captured["config"]["book_dir"] == str(book_dir)
    assert captured["config"]["narrator_voice"] == "af_heart"
    assert captured["config"]["speed"] == 1.1
    assert captured["config"]["quality"] == "sd"
    assert captured["config"]["format"] == "mp3"


def test_reconvert_chapter_endpoint_rejects_invalid_voice(app_client):
    client, _data_dir, library_dir = app_client
    book_id, _book_dir, _metadata = create_library_book(library_dir)

    response = client.post(
        f"/api/book/{book_id}/chapter/1/reconvert",
        json={"narrator_voice": "not-a-real-voice"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid narrator voice"