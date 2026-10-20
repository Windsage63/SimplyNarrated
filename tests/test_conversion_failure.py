from src.core.job_manager import get_job_manager


def test_failed_pdf_conversion_exposes_reason_and_saves_traceback(app_client, monkeypatch):
    client, data_dir, _library_dir = app_client
    error = "Failed to load PDF layout model: [WinError 233] No process is on the other end of the pipe"

    def broken_pdf_import(*_args):
        raise RuntimeError(error)

    monkeypatch.setattr("src.core.pipeline.convert_source_document", broken_pdf_import)
    uploaded = client.post(
        "/api/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert uploaded.status_code == 200
    job_id = uploaded.json()["job_id"]
    response = client.post("/api/generate", json={
        "job_id": job_id,
        "model": "kokoro",
        "narrator_voice": "af_heart",
    })
    assert response.status_code == 200

    async def wait_for_conversion():
        await get_job_manager().get_job(job_id)._task

    client.portal.call(wait_for_conversion)
    status = client.get(f"/api/status/{job_id}").json()
    assert status["status"] == "failed"
    assert status["error"] == error
    assert status["activity_log"][-1]["message"] == f"Error: {error}"

    log = (data_dir / "logs" / "simplynarrated.log").read_text(encoding="utf-8")
    assert job_id in log
    assert "Traceback (most recent call last)" in log
    assert "broken_pdf_import" in log
    assert error in log


def test_pending_conversion_has_no_error(app_client):
    client, _data_dir, _library_dir = app_client
    uploaded = client.post(
        "/api/upload",
        files={"file": ("sample.txt", b"Hello world", "text/plain")},
    )
    status = client.get(f"/api/status/{uploaded.json()['job_id']}").json()
    assert status["status"] == "pending"
    assert status["error"] is None
