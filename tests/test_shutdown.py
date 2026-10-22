import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from src.core.job_manager import JobManager
from src.models.schemas import JobStatus


def test_shutdown_cancels_running_and_queued_jobs_and_persists_state(tmp_path):
    manager = JobManager(str(tmp_path / "data"))
    running = manager.create_job("running.txt", "running.txt")
    queued = manager.create_job("queued.txt", "queued.txt")
    completed = manager.create_job("completed.txt", "completed.txt")
    completed.status = JobStatus.COMPLETED
    calls = []

    async def scenario():
        started = asyncio.Event()

        async def process(job, _config):
            calls.append(job.id)
            started.set()
            await asyncio.Event().wait()

        assert await manager.start_job(running.id, {}, process)
        assert await manager.start_job(queued.id, {}, process)
        await started.wait()
        assert running.status == JobStatus.PROCESSING
        assert queued.status == JobStatus.PENDING

        await manager.shutdown()
        assert running._task.done()
        assert queued._task.done()
        assert calls == [running.id]
        assert completed.status == JobStatus.COMPLETED
        for job in (running, queued):
            assert job.status == JobStatus.CANCELLED
            assert job.completed_at is not None
            assert any("application is closing" in entry.message for entry in job.activity_log)

        new_job = manager.create_job("new.txt", "new.txt")
        assert not await manager.start_job(new_job.id, {}, process)

    asyncio.run(scenario())
    saved = json.loads((tmp_path / "data" / "jobs.json").read_text(encoding="utf-8"))
    states = {job["id"]: job for job in saved["jobs"]}
    for job in (running, queued):
        assert states[job.id]["status"] == "cancelled"
        assert states[job.id]["completed_at"] is not None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows console control events")
def test_windows_ctrl_c_stops_server_even_if_parent_disabled_interrupts(tmp_path):
    # A separate, hidden console confines CTRL_C_EVENT to this test process.
    # Inherit/simulate the Windows ignore flag that previously swallowed Ctrl+C.
    script = textwrap.dedent(r'''
        import asyncio, ctypes, pathlib, sys, uvicorn
        ctypes.windll.kernel32.SetConsoleCtrlHandler(None, True)
        config = uvicorn.Config('src.main:app', host='127.0.0.1', port=0)
        original_load = config.load
        def load():
            original_load()
            import src.main as main
            main.DATA_DIR = sys.argv[1]
            main.LIBRARY_DIR = str(pathlib.Path(main.DATA_DIR) / 'library')
        config.load = load
        server = uvicorn.Server(config)
        sent = False
        received = False
        async def notify():
            global sent, received
            if sent:
                return
            sent = True
            assert ctypes.windll.kernel32.GenerateConsoleCtrlEvent(0, 0)
            await asyncio.sleep(0.5)
            received = server.should_exit
            server.should_exit = True  # Bound the test if the interrupt is lost.
        config.callback_notify = notify
        try:
            server.run()
        except KeyboardInterrupt:
            pass
        assert received, 'Ctrl+C was ignored by the running server'
        print('CTRL_C_SHUTDOWN_OK', flush=True)
    ''')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(tmp_path / "server-data")],
        cwd=Path(__file__).resolve().parents[1],
        env=dict(os.environ, HF_HUB_OFFLINE="1", HF_HUB_DISABLE_PROGRESS_BARS="1"),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        startupinfo=startup,
        capture_output=True,
        text=True,
        timeout=25,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CTRL_C_SHUTDOWN_OK" in result.stdout
    assert "Application shutdown complete" in result.stderr
