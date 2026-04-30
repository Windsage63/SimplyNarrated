import json
from datetime import datetime, timedelta

from src.core.job_manager import Job, JobManager
from src.models.schemas import JobStatus


def _job_payload(job_id, *, status, created_at, completed_at=None):
    return {
        "id": job_id,
        "filename": f"{job_id}.txt",
        "file_path": f"data/uploads/{job_id}.txt",
        "status": status,
        "progress": 100.0 if status == JobStatus.COMPLETED.value else 0.0,
        "current_chapter": 0,
        "total_chapters": 0,
        "created_at": created_at.isoformat(),
        "started_at": None,
        "completed_at": completed_at.isoformat() if completed_at else None,
        "activity_log": [],
        "config": {},
        "output_dir": None,
        "error": None,
    }


def test_job_manager_prunes_terminal_jobs_older_than_three_days_on_load(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    old_time = now - timedelta(days=4)
    recent_time = now - timedelta(days=1)

    payload = {
        "jobs": [
            _job_payload(
                "old-completed",
                status=JobStatus.COMPLETED.value,
                created_at=old_time,
                completed_at=old_time,
            ),
            _job_payload(
                "recent-completed",
                status=JobStatus.COMPLETED.value,
                created_at=recent_time,
                completed_at=recent_time,
            ),
            _job_payload(
                "old-pending",
                status=JobStatus.PENDING.value,
                created_at=old_time,
            ),
        ]
    }
    (data_dir / "jobs.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    manager = JobManager(str(data_dir))

    assert manager.get_job("old-completed") is None
    assert manager.get_job("recent-completed") is not None
    assert manager.get_job("old-pending") is not None


def test_persist_prunes_expired_terminal_jobs_before_write(tmp_path):
    data_dir = tmp_path / "data"
    manager = JobManager(str(data_dir))

    old_completed = Job(
        id="old-completed",
        filename="old.txt",
        file_path=str(data_dir / "uploads" / "old.txt"),
        status=JobStatus.COMPLETED,
        created_at=datetime.now() - timedelta(days=5),
        completed_at=datetime.now() - timedelta(days=4),
    )
    recent_pending = Job(
        id="recent-pending",
        filename="recent.txt",
        file_path=str(data_dir / "uploads" / "recent.txt"),
        status=JobStatus.PENDING,
        created_at=datetime.now(),
    )
    manager._jobs = {
        old_completed.id: old_completed,
        recent_pending.id: recent_pending,
    }

    manager._persist_jobs()

    persisted = json.loads((data_dir / "jobs.json").read_text(encoding="utf-8"))
    persisted_ids = {job["id"] for job in persisted["jobs"]}

    assert persisted_ids == {"recent-pending"}
    assert manager.get_job("old-completed") is None