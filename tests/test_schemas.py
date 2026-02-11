"""
Tests for Pydantic schemas and enum definitions.
"""

import pytest
from pydantic import ValidationError

from src.models.schemas import (
    AudioQuality,
    AudioFormat,
    JobStatus,
    GenerateRequest,
    UploadResponse,
    BookInfo,
    ChapterInfo,
    StatusResponse,
    VoiceInfo,
    VoicesResponse,
    ActivityLogEntry,
)
from datetime import datetime


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestAudioQualityEnum:
    def test_values(self):
        assert AudioQuality.SD.value == "sd"
        assert AudioQuality.HD.value == "hd"
        assert AudioQuality.ULTRA.value == "ultra"

    def test_all_members(self):
        assert len(AudioQuality) == 3


class TestAudioFormatEnum:
    def test_values(self):
        assert AudioFormat.MP3.value == "mp3"

    def test_only_mp3(self):
        assert len(AudioFormat) == 1


class TestJobStatusEnum:
    def test_all_statuses(self):
        expected = {"pending", "processing", "completed", "failed", "cancelled"}
        actual = {s.value for s in JobStatus}
        assert actual == expected


# ---------------------------------------------------------------------------
# Request schema tests
# ---------------------------------------------------------------------------


class TestGenerateRequest:
    def test_defaults(self):
        req = GenerateRequest(job_id="abc-123")
        assert req.narrator_voice == "af_heart"
        assert req.dialogue_voice is None
        assert req.speed == 1.0
        assert req.quality == AudioQuality.SD
        assert req.format == AudioFormat.MP3

    def test_speed_minimum(self):
        with pytest.raises(ValidationError):
            GenerateRequest(job_id="x", speed=0.3)

    def test_speed_maximum(self):
        with pytest.raises(ValidationError):
            GenerateRequest(job_id="x", speed=2.5)

    def test_valid_speed_boundaries(self):
        low = GenerateRequest(job_id="x", speed=0.5)
        high = GenerateRequest(job_id="x", speed=2.0)
        assert low.speed == 0.5
        assert high.speed == 2.0

    def test_custom_values(self):
        req = GenerateRequest(
            job_id="test",
            narrator_voice="bm_lewis",
            speed=1.5,
            quality=AudioQuality.ULTRA,
            format=AudioFormat.MP3,
        )
        assert req.narrator_voice == "bm_lewis"
        assert req.quality == AudioQuality.ULTRA
        assert req.format == AudioFormat.MP3


# ---------------------------------------------------------------------------
# Response schema tests
# ---------------------------------------------------------------------------


class TestUploadResponse:
    def test_construction(self):
        resp = UploadResponse(
            job_id="j1",
            filename="book.txt",
            file_size=1024,
            estimated_time="~1 minutes",
            chapters_detected=5,
        )
        assert resp.job_id == "j1"
        assert resp.file_size == 1024
        assert resp.chapters_detected == 5

    def test_defaults(self):
        resp = UploadResponse(job_id="j1", filename="f.txt", file_size=100)
        assert resp.estimated_time is None
        assert resp.chapters_detected == 0


class TestBookInfo:
    def test_with_chapters(self):
        chapters = [
            ChapterInfo(number=1, title="Intro", completed=True),
            ChapterInfo(number=2, title="Body", duration="5:00"),
        ]
        book = BookInfo(
            id="b1",
            title="My Book",
            total_chapters=2,
            created_at=datetime.now(),
            chapters=chapters,
        )
        assert book.total_chapters == 2
        assert len(book.chapters) == 2
        assert book.chapters[0].completed is True
        assert book.chapters[1].duration == "5:00"
        assert book.author is None

    def test_minimal(self):
        book = BookInfo(
            id="b2", title="Minimal", total_chapters=0, created_at=datetime.now()
        )
        assert book.chapters == []


class TestStatusResponse:
    def test_construction(self):
        resp = StatusResponse(
            job_id="j1",
            status=JobStatus.PROCESSING,
            progress=50.0,
            current_chapter=2,
            total_chapters=4,
        )
        assert resp.progress == 50.0
        assert resp.status == JobStatus.PROCESSING


class TestVoicesResponse:
    def test_construction(self):
        voices = [
            VoiceInfo(id="af_heart", name="Heart", description="Warm", gender="female")
        ]
        resp = VoicesResponse(voices=voices, total=1)
        assert resp.total == 1
        assert resp.voices[0].id == "af_heart"
