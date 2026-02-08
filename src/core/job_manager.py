"""
@fileoverview BookTalk - Job Manager, Handles conversion job state management and background task execution
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

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.uploads_dir = os.path.join(data_dir, "uploads")
        self.library_dir = os.path.join(data_dir, "library")
        self._jobs: Dict[str, Job] = {}

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
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def _add_activity(self, job: Job, message: str, status: str = "info") -> None:
        """Add an activity log entry to a job."""
        entry = ActivityLogEntry(
            timestamp=datetime.now(),
            message=message,
            status=status,
        )
        job.activity_log.append(entry)

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

    async def start_job(
        self, job_id: str, config: dict, process_func: Callable[[Job, dict], Any]
    ) -> bool:
        """Start processing a job in the background."""
        job = self.get_job(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now()
        job.config = config
        job.output_dir = os.path.join(self.library_dir, job_id)
        os.makedirs(job.output_dir, exist_ok=True)

        self._add_activity(job, "Starting conversion...", "info")

        # Create background task
        job._task = asyncio.create_task(self._run_job(job, process_func, config))
        return True

    async def _run_job(self, job: Job, process_func: Callable, config: dict) -> None:
        """Execute the job processing function."""
        try:
            await process_func(job, config)
            if job.status == JobStatus.PROCESSING:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = datetime.now()
                self._add_activity(job, "Conversion completed!", "success")
        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            self._add_activity(job, "Conversion cancelled", "warning")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            self._add_activity(job, f"Error: {str(e)}", "error")

    def cancel_job(self, job_id: str) -> bool:
        """Cancel an in-progress job."""
        job = self.get_job(job_id)
        if not job or job.status != JobStatus.PROCESSING:
            return False

        if job._task and not job._task.done():
            job._task.cancel()

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
    _job_manager = JobManager(data_dir)
    return _job_manager
