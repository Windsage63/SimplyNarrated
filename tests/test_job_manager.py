"""
Tests for the JobManager (in-memory job state + filesystem output dirs).
"""

import asyncio
import pytest
from datetime import datetime

from src.models.schemas import JobStatus
from src.core.job_manager import JobManager, Job


# ---------------------------------------------------------------------------
# Job creation & retrieval
# ---------------------------------------------------------------------------


class TestCreateJob:
    def test_creates_with_pending_status(self, job_manager):
        job = job_manager.create_job("book.txt", "/tmp/book.txt")
        assert job.status == JobStatus.PENDING
        assert job.filename == "book.txt"
        assert job.progress == 0.0

    def test_assigns_uuid(self, job_manager):
        job = job_manager.create_job("a.txt", "/a.txt")
        assert len(job.id) == 36  # UUID format

    def test_retrievable(self, job_manager):
        job = job_manager.create_job("b.txt", "/b.txt")
        fetched = job_manager.get_job(job.id)
        assert fetched is job

    def test_get_nonexistent(self, job_manager):
        assert job_manager.get_job("no-such-id") is None


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------


class TestActivityLog:
    def test_creation_adds_entry(self, job_manager):
        job = job_manager.create_job("c.txt", "/c.txt")
        assert len(job.activity_log) == 1
        assert "created" in job.activity_log[0].message.lower()

    def test_add_custom_activity(self, job_manager):
        job = job_manager.create_job("d.txt", "/d.txt")
        job_manager._add_activity(job, "Custom message", "success")
        assert len(job.activity_log) == 2
        assert job.activity_log[1].message == "Custom message"
        assert job.activity_log[1].status == "success"


# ---------------------------------------------------------------------------
# Progress updates
# ---------------------------------------------------------------------------


class TestUpdateProgress:
    def test_updates_fields(self, job_manager):
        job = job_manager.create_job("e.txt", "/e.txt")
        job_manager.update_progress(job.id, 50.0, current_chapter=2, message="Half done")
        assert job.progress == 50.0
        assert job.current_chapter == 2

    def test_clamps_progress(self, job_manager):
        job = job_manager.create_job("f.txt", "/f.txt")
        job_manager.update_progress(job.id, 150.0)
        assert job.progress == 100.0
        job_manager.update_progress(job.id, -10.0)
        assert job.progress == 0.0


# ---------------------------------------------------------------------------
# Start / run / cancel
# ---------------------------------------------------------------------------


class TestStartJob:
    async def test_changes_status_to_processing(self, job_manager):
        job = job_manager.create_job("g.txt", "/g.txt")

        async def dummy(j, cfg):
            await asyncio.sleep(0.1)

        ok = await job_manager.start_job(job.id, {}, dummy)
        assert ok is True
        assert job.status == JobStatus.PROCESSING
        assert job.output_dir is not None

        # Wait for the task to finish
        if job._task:
            await job._task

    async def test_start_already_started_fails(self, job_manager):
        job = job_manager.create_job("h.txt", "/h.txt")

        async def dummy(j, cfg):
            await asyncio.sleep(0.1)

        await job_manager.start_job(job.id, {}, dummy)
        ok = await job_manager.start_job(job.id, {}, dummy)
        assert ok is False

        if job._task:
            await job._task

    async def test_completes_successfully(self, job_manager):
        job = job_manager.create_job("i.txt", "/i.txt")

        async def dummy(j, cfg):
            await asyncio.sleep(0.05)

        await job_manager.start_job(job.id, {}, dummy)
        if job._task:
            await job._task

        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100.0

    async def test_handles_failure(self, job_manager):
        job = job_manager.create_job("j.txt", "/j.txt")

        async def failing(j, cfg):
            raise RuntimeError("boom")

        await job_manager.start_job(job.id, {}, failing)
        if job._task:
            await job._task

        assert job.status == JobStatus.FAILED
        assert "boom" in job.error


class TestCancelJob:
    async def test_cancel_running_job(self, job_manager):
        job = job_manager.create_job("k.txt", "/k.txt")

        async def slow(j, cfg):
            await asyncio.sleep(10)

        await job_manager.start_job(job.id, {}, slow)
        await asyncio.sleep(0)          # let task enter the coroutine
        ok = job_manager.cancel_job(job.id)
        assert ok is True

        # Wait for the task to fully finish (CancelledError handling)
        await asyncio.sleep(0.2)
        assert job.status == JobStatus.CANCELLED

    def test_cancel_nonexistent(self, job_manager):
        assert job_manager.cancel_job("nope") is False

    def test_cancel_pending_fails(self, job_manager):
        job = job_manager.create_job("l.txt", "/l.txt")
        assert job_manager.cancel_job(job.id) is False


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


class TestCountProcessingJobs:
    async def test_counts_correctly(self, job_manager):
        async def slow(j, cfg):
            await asyncio.sleep(10)

        j1 = job_manager.create_job("a.txt", "/a.txt")
        j2 = job_manager.create_job("b.txt", "/b.txt")
        j3 = job_manager.create_job("c.txt", "/c.txt")

        await job_manager.start_job(j1.id, {}, slow)
        await job_manager.start_job(j2.id, {}, slow)
        # j3 stays PENDING

        assert job_manager.count_processing_jobs() == 2

        # Cleanup
        job_manager.cancel_job(j1.id)
        job_manager.cancel_job(j2.id)
        await asyncio.sleep(0.2)
