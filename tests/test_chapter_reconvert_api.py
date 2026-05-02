from src.core.job_manager import get_job_manager
from src.core.job_manager import init_job_manager
from src.core.chapter_reconvert import process_chapter_reconvert_job
from src.models.schemas import JobStatus

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


def test_models_endpoint_returns_kokoro_only_in_phase_1(app_client):
    client, _data_dir, _library_dir = app_client

    response = client.get("/api/models")

    assert response.status_code == 200
    assert response.json() == {
        "models": ["kokoro"],
        "active_model": "kokoro",
    }


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
            "model": "kokoro",
            "narrator_voice": "af_heart",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert captured["process_name"] == "process_chapter_reconvert_job"
    assert captured["config"]["book_id"] == book_id
    assert captured["config"]["chapter_number"] == 1
    assert captured["config"]["book_dir"] == str(book_dir)
    assert captured["config"]["model"] == "kokoro"
    assert captured["config"]["narrator_voice"] == "af_heart"


def test_reconvert_chapter_endpoint_rejects_invalid_voice(app_client):
    client, _data_dir, library_dir = app_client
    book_id, _book_dir, _metadata = create_library_book(library_dir)

    response = client.post(
        f"/api/book/{book_id}/chapter/1/reconvert",
        json={"narrator_voice": "not-a-real-voice"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid narrator voice"


def test_reconvert_chapter_endpoint_reuses_active_job_for_same_book_and_chapter(
    app_client,
    monkeypatch,
):
    client, _data_dir, library_dir = app_client
    book_id, book_dir, _metadata = create_library_book(library_dir, chapter_text="Ready for reconvert")
    job_manager = get_job_manager()
    existing_job = job_manager.create_job("chapter_01_reconvert", str(book_dir / "chapter_01.txt"))
    existing_job.status = JobStatus.PROCESSING
    existing_job.config = {
        "job_type": "chapter_reconvert",
        "book_id": book_id,
        "chapter_number": 1,
    }

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("start_job should not be called for duplicate reconvert requests")

    monkeypatch.setattr(job_manager, "start_job", fail_if_called)

    response = client.post(
        f"/api/book/{book_id}/chapter/1/reconvert",
        json={
            "model": "kokoro",
            "narrator_voice": "af_heart",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processing",
        "job_id": existing_job.id,
        "book_id": book_id,
        "chapter": 1,
    }


def test_book_endpoint_exposes_model_and_voice(app_client):
    client, _data_dir, library_dir = app_client
    book_id, _book_dir, _metadata = create_library_book(
        library_dir,
        model="kokoro",
        voice="af_heart",
    )

    response = client.get(f"/api/book/{book_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "kokoro"
    assert payload["voice"] == "af_heart"


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
            self.loaded = False

        def is_loaded(self):
            return self.loaded

        def load(self):
            self.loaded = True

        def unload(self):
            self.loaded = False

        def generate_speech(self, text, voice_id):
            return np.zeros(32, dtype=np.float32), 24000

    class FakeTTSManager:
        def __init__(self):
            self.model = FakeTTSEngine()

        def switch_model(self, _model_name):
            if not self.model.is_loaded():
                self.model.load()
            return self.model

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
    monkeypatch.setattr("src.core.chapter_reconvert.get_tts_manager", lambda: FakeTTSManager())
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
                "model": "kokoro",
                "narrator_voice": "af_heart",
            },
        )
    )

    assert "switch_model" in offloaded_names
    assert "generate_speech" in offloaded_names
    assert "fake_encode_audio" in offloaded_names
    assert "fake_embed_mp3_metadata" in offloaded_names
    assert "update_metadata_file" in offloaded_names


def test_process_chapter_reconvert_job_stops_when_cancelled_after_tts_returns(
    tmp_path,
    monkeypatch,
):
    import asyncio

    import numpy as np

    data_dir = tmp_path / "data"
    library_dir = data_dir / "library"
    library_dir.mkdir(parents=True, exist_ok=True)
    job_manager = init_job_manager(str(data_dir))

    book_id, book_dir, _metadata = create_library_book(
        library_dir,
        chapter_text="Edited chapter text for reconvert.",
    )
    job = job_manager.create_job("chapter_01_reconvert", str(book_dir / "chapter_01.txt"))
    job.status = JobStatus.PROCESSING

    class FakeTTSEngine:
        def is_loaded(self):
            return True

        def load(self):
            return None

        def unload(self):
            return None

        def generate_speech(self, text, voice_id):
            job.status = JobStatus.CANCELLED
            return np.zeros(32, dtype=np.float32), 24000

    class FakeTTSManager:
        def switch_model(self, _model_name):
            return FakeTTSEngine()

    async def fake_run_blocking(function, *args, **kwargs):
        return function(*args, **kwargs)

    def fail_encode_audio(*args, **kwargs):
        raise AssertionError("encode_audio should not run after cancellation")

    def fail_update_metadata_file(*args, **kwargs):
        raise AssertionError("metadata update should not run after cancellation")

    monkeypatch.setattr("src.core.chapter_reconvert._run_blocking", fake_run_blocking)
    monkeypatch.setattr("src.core.chapter_reconvert.get_tts_manager", lambda: FakeTTSManager())
    monkeypatch.setattr("src.core.chapter_reconvert.encode_audio", fail_encode_audio)
    monkeypatch.setattr("src.core.chapter_reconvert.update_metadata_file", fail_update_metadata_file)

    asyncio.run(
        process_chapter_reconvert_job(
            job,
            {
                "book_id": book_id,
                "chapter_number": 1,
                "book_dir": str(book_dir),
                "output_dir": str(book_dir),
                "model": "kokoro",
                "narrator_voice": "af_heart",
            },
        )
    )

    assert not list(book_dir.glob("chapter_01.*.tmp.mp3"))