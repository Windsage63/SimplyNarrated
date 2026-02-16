"""
@fileoverview SimplyNarrated - Job Manager, Handles conversion job state management and background task execution
@author Timothy Mallory <windsage@live.com>
@license Apache-2.0
@copyright 2026 Timothy Mallory <windsage@live.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import uuid
import os
import json
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field

from src.models.schemas import JobStatus, ActivityLogEntry


@dataclass
class Job:
    """Represents a conversion job."""

    id: str
    filename: str
    file_path: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    current_chapter: int = 0
    total_chapters: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    activity_log: list = field(default_factory=list)
    config: dict = field(default_factory=dict)
    output_dir: Optional[str] = None
    error: Optional[str] = None
    _task: Optional[asyncio.Task] = field(default=None, repr=False)


class JobManager:
    """Manages conversion jobs and their lifecycle."""

    def __init__(self, data_dir: str, max_concurrent_jobs: int = 1):
        self.data_dir = data_dir
        self.uploads_dir = os.path.join(data_dir, "uploads")
        self.library_dir = os.path.join(data_dir, "library")
        self.jobs_file = os.path.join(data_dir, "jobs.json")
        self._jobs: Dict[str, Job] = {}
        self.max_concurrent_jobs = max(1, max_concurrent_jobs)
        self._semaphore = asyncio.Semaphore(self.max_concurrent_jobs)

        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.library_dir, exist_ok=True)
        self._load_jobs()
        self._recover_jobs_after_restart()

    @staticmethod
    def _serialize_activity(entry: ActivityLogEntry) -> dict:
        return {
            "timestamp": entry.timestamp.isoformat(),
            "message": entry.message,
            "status": entry.status,
        }

    @staticmethod
    def _deserialize_activity(entry: dict) -> ActivityLogEntry:
        ts = entry.get("timestamp")
        timestamp = datetime.fromisoformat(ts) if ts else datetime.now()
        return ActivityLogEntry(
            timestamp=timestamp,
            message=entry.get("message", ""),
            status=entry.get("status", "info"),
        )

    def _serialize_job(self, job: Job) -> dict:
        return {
            "id": job.id,
            "filename": job.filename,
            "file_path": job.file_path,
            "status": job.status.value,
            "progress": job.progress,
            "current_chapter": job.current_chapter,
            "total_chapters": job.total_chapters,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "activity_log": [
                self._serialize_activity(entry) for entry in job.activity_log
            ],
            "config": job.config,
            "output_dir": job.output_dir,
            "error": job.error,
        }

    def _deserialize_job(self, data: dict) -> Job:
        return Job(
            id=data["id"],
            filename=data.get("filename", "unknown"),
            file_path=data.get("file_path", ""),
            status=JobStatus(data.get("status", JobStatus.PENDING.value)),
            progress=float(data.get("progress", 0.0)),
            current_chapter=int(data.get("current_chapter", 0)),
            total_chapters=int(data.get("total_chapters", 0)),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            activity_log=[
                self._deserialize_activity(entry) for entry in data.get("activity_log", [])
            ],
            config=data.get("config", {}),
            output_dir=data.get("output_dir"),
            error=data.get("error"),
        )

    def _persist_jobs(self) -> None:
        payload = {"jobs": [self._serialize_job(job) for job in self._jobs.values()]}
        with open(self.jobs_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _load_jobs(self) -> None:
        if not os.path.exists(self.jobs_file):
            return

        try:
            with open(self.jobs_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            for raw in payload.get("jobs", []):
                job = self._deserialize_job(raw)
                self._jobs[job.id] = job
        except Exception:
            # If persisted state is unreadable, continue with empty in-memory jobs.
            self._jobs = {}

    def _recover_jobs_after_restart(self) -> None:
        changed = False
        for job in self._jobs.values():
            if job.status == JobStatus.PROCESSING:
                job.status = JobStatus.FAILED
                job.error = "Job interrupted by application restart"
                job.completed_at = datetime.now()
                self._add_activity(
                    job,
                    "Job marked failed after restart while previously processing",
                    "warning",
                )
                changed = True

        if changed:
            self._persist_jobs()

    def create_job(self, filename: str, file_path: str) -> Job:
        """Create a new conversion job."""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            filename=filename,
            file_path=file_path,
        )
        self._jobs[job_id] = job
        self._add_activity(job, f"Job created for file: {filename}")
        self._persist_jobs()
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        """Get all jobs currently tracked in the ledger."""
        return list(self._jobs.values())

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the ledger."""
        if job_id not in self._jobs:
            return False
        del self._jobs[job_id]
        self._persist_jobs()
        return True

    def _add_activity(self, job: Job, message: str, status: str = "info") -> None:
        """Add an activity log entry to a job."""
        entry = ActivityLogEntry(
            timestamp=datetime.now(),
            message=message,
            status=status,
        )
        job.activity_log.append(entry)
        self._persist_jobs()

    def add_activity(self, job: Job, message: str, status: str = "info") -> None:
        """Public wrapper for recording job activity."""
        self._add_activity(job, message, status)

    def update_progress(
        self,
        job_id: str,
        progress: float,
        current_chapter: int = 0,
        message: Optional[str] = None,
    ) -> None:
        """Update job progress."""
        job = self.get_job(job_id)
        if job:
            job.progress = min(100.0, max(0.0, progress))
            job.current_chapter = current_chapter
            if message:
                self._add_activity(job, message)
            else:
                self._persist_jobs()

    async def start_job(
        self, job_id: str, config: dict, process_func: Callable[[Job, dict], Any]
    ) -> bool:
        """Queue processing of a job in the background with bounded concurrency."""
        job = self.get_job(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False
        if job._task and not job._task.done():
            return False

        job.config = config
        job.output_dir = os.path.join(self.library_dir, job_id)
        os.makedirs(job.output_dir, exist_ok=True)

        self._add_activity(job, "Job queued for conversion...", "info")
        self._persist_jobs()

        # Create background task that waits for execution slot
        job._task = asyncio.create_task(self._run_with_limit(job, process_func, config))
        return True

    async def _run_with_limit(self, job: Job, process_func: Callable, config: dict) -> None:
        try:
            async with self._semaphore:
                if job.status == JobStatus.CANCELLED:
                    return

                job.status = JobStatus.PROCESSING
                job.started_at = datetime.now()
                self._add_activity(job, "Starting conversion...", "info")
                await self._run_job(job, process_func, config)
        except asyncio.CancelledError:
            if job.status not in {JobStatus.COMPLETED, JobStatus.FAILED}:
                job.status = JobStatus.CANCELLED
                self._add_activity(job, "Conversion cancelled", "warning")
            raise

    async def _run_job(self, job: Job, process_func: Callable, config: dict) -> None:
        """Execute the job processing function."""
        try:
            await process_func(job, config)
            if job.status == JobStatus.PROCESSING:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = datetime.now()
                self._add_activity(job, "Conversion completed!", "success")
                self._persist_jobs()
        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            self._add_activity(job, "Conversion cancelled", "warning")
            self._persist_jobs()
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()
            self._add_activity(job, f"Error: {str(e)}", "error")
            self._persist_jobs()

    def cancel_job(self, job_id: str) -> bool:
        """Cancel an in-progress job."""
        job = self.get_job(job_id)
        if not job:
            return False

        is_processing = job.status == JobStatus.PROCESSING
        is_queued = job.status == JobStatus.PENDING and job._task is not None

        if not is_processing and not is_queued:
            return False

        if job._task and not job._task.done():
            job._task.cancel()

        if is_queued:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            self._add_activity(job, "Queued job cancelled", "warning")
            self._persist_jobs()

        return True

    def count_processing_jobs(self) -> int:
        """Count jobs currently processing."""
        return sum(1 for j in self._jobs.values() if j.status == JobStatus.PROCESSING)

    def get_time_remaining(self, job: Job) -> Optional[str]:
        """Estimate time remaining for a job."""
        if job.status != JobStatus.PROCESSING or job.progress == 0:
            return None

        if job.started_at:
            elapsed = (datetime.now() - job.started_at).total_seconds()
            if job.progress > 0:
                total_estimated = elapsed / (job.progress / 100)
                remaining = total_estimated - elapsed
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                return f"~{minutes}m {seconds}s"
        return None

    def get_processing_rate(self, job: Job) -> Optional[str]:
        """Get the current processing rate."""
        if job.status != JobStatus.PROCESSING or not job.started_at:
            return None

        elapsed = (datetime.now() - job.started_at).total_seconds()
        if elapsed > 0 and job.progress > 0:
            # Rough estimate: 100 chars per percent for a typical book
            chars_processed = int(job.progress * 100)
            rate = int(chars_processed / elapsed)
            return f"{rate} chars/sec"
        return None


# Global job manager instance (initialized in main.py lifespan)
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get the global job manager instance."""
    global _job_manager
    if _job_manager is None:
        raise RuntimeError("JobManager not initialized")
    return _job_manager


def init_job_manager(data_dir: str) -> JobManager:
    """Initialize the global job manager."""
    global _job_manager
    max_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))
    _job_manager = JobManager(data_dir, max_concurrent_jobs=max_jobs)
    return _job_manager
