from src.core.job_manager import get_job_manager
from src.core.job_manager import init_job_manager
from src.core.chapter_reconvert import process_chapter_reconvert_job

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


def test_update_book_metadata_endpoint_offloads_sync_work(app_client, monkeypatch):
    client, _data_dir, library_dir = app_client
    book_id, book_dir, _metadata = create_library_book(library_dir)
    offloaded_names = []

    def fake_retag_book_mp3_files(book_dir_arg, metadata):
        return None

    async def fake_run_blocking(function, *args, **kwargs):
        offloaded_names.append(getattr(function, "__name__", type(function).__name__))
        return function(*args, **kwargs)

    monkeypatch.setattr("src.api.routes._run_blocking", fake_run_blocking)
    monkeypatch.setattr("src.api.routes.retag_book_mp3_files", fake_retag_book_mp3_files)

    response = client.patch(
        f"/api/book/{book_id}",
        json={"title": "Updated Title"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
    assert "update_book_metadata" in offloaded_names
    assert "fake_retag_book_mp3_files" in offloaded_names
    assert "Updated Title" in (book_dir / "metadata.json").read_text(encoding="utf-8")


def test_process_chapter_reconvert_job_offloads_blocking_steps(tmp_path, monkeypatch):
    import asyncio

    import numpy as np

    data_dir = tmp_path / "data"
    library_dir = data_dir / "library"
    library_dir.mkdir(parents=True, exist_ok=True)
    job_manager = init_job_manager(str(data_dir))

    book_id, book_dir, _metadata = create_library_book(
        library_dir,
        chapter_text="Edited chapter text for reconvert.",
        title="Reconvert Test Book",
        author="Reconvert Author",
    )
    job = job_manager.create_job("chapter_01_reconvert", str(book_dir / "chapter_01.txt"))
    offloaded_names = []

    class FakeTTSEngine:
        def __init__(self):
            self.initialized = False

        def is_initialized(self):
            return self.initialized

        def initialize(self):
            self.initialized = True

        def generate_speech(self, text, voice_id, speed):
            return np.zeros(32, dtype=np.float32), 24000

    def fake_encode_audio(_audio, _sample_rate, output_path, _settings):
        with open(output_path, "wb") as handle:
            handle.write(b"mp3")
        return output_path

    def fake_embed_mp3_metadata(file_path, **kwargs):
        return file_path

    class FakeAudioSegment:
        duration_seconds = 12.0

    async def fake_run_blocking(function, *args, **kwargs):
        offloaded_names.append(getattr(function, "__name__", type(function).__name__))
        return function(*args, **kwargs)

    monkeypatch.setattr("src.core.chapter_reconvert._run_blocking", fake_run_blocking)
    monkeypatch.setattr("src.core.chapter_reconvert.get_tts_engine", lambda: FakeTTSEngine())
    monkeypatch.setattr("src.core.chapter_reconvert.encode_audio", fake_encode_audio)
    monkeypatch.setattr("src.core.chapter_reconvert.embed_mp3_metadata", fake_embed_mp3_metadata)
    monkeypatch.setattr(
        "src.core.chapter_reconvert.AudioSegment.from_file",
        lambda path: FakeAudioSegment(),
    )

    asyncio.run(
        process_chapter_reconvert_job(
            job,
            {
                "book_id": book_id,
                "chapter_number": 1,
                "book_dir": str(book_dir),
                "output_dir": str(book_dir),
                "narrator_voice": "af_heart",
                "speed": 1.0,
                "quality": "sd",
                "format": "mp3",
            },
        )
    )

    assert "initialize" in offloaded_names
    assert "generate_speech" in offloaded_names
    assert "fake_encode_audio" in offloaded_names
    assert "fake_embed_mp3_metadata" in offloaded_names
    assert "update_metadata_file" in offloaded_names