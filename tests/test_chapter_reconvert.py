"""
Unit tests for src/core/chapter_reconvert.py helpers.
"""

import asyncio
import os

import pytest

from src.core.chapter_reconvert import (
    _parse_duration_to_seconds,
    _format_total_duration_from_chapters,
    _replace_with_retry,
)


# ---------------------------------------------------------------------------
# _parse_duration_to_seconds
# ---------------------------------------------------------------------------


class TestParseDurationToSeconds:
    def test_mm_ss(self):
        assert _parse_duration_to_seconds("1:30") == 90.0

    def test_hh_mm_ss(self):
        assert _parse_duration_to_seconds("1:02:03") == 3723.0

    def test_empty(self):
        assert _parse_duration_to_seconds("") == 0.0

    def test_none_like(self):
        assert _parse_duration_to_seconds(None) == 0.0

    def test_invalid(self):
        assert _parse_duration_to_seconds("not-a-time") == 0.0

    def test_zero(self):
        assert _parse_duration_to_seconds("0:00") == 0.0


# ---------------------------------------------------------------------------
# _format_total_duration_from_chapters
# ---------------------------------------------------------------------------


class TestFormatTotalDurationFromChapters:
    def test_sums_durations(self):
        chapters = [
            {"duration": "1:00"},
            {"duration": "2:30"},
        ]
        result = _format_total_duration_from_chapters(chapters)
        # 60 + 150 = 210 seconds = 3:30
        assert result == "3:30"

    def test_empty_list(self):
        result = _format_total_duration_from_chapters([])
        assert result == "0:00"

    def test_missing_duration_key(self):
        chapters = [{"title": "Chapter 1"}]
        result = _format_total_duration_from_chapters(chapters)
        assert result == "0:00"


# ---------------------------------------------------------------------------
# _replace_with_retry (async)
# ---------------------------------------------------------------------------


class TestReplaceWithRetry:
    async def test_successful_replace(self, tmp_path):
        src = tmp_path / "source.tmp"
        dst = tmp_path / "destination.mp3"
        src.write_bytes(b"audio data")

        await _replace_with_retry(str(src), str(dst))

        assert dst.exists()
        assert not src.exists()
        assert dst.read_bytes() == b"audio data"

    async def test_raises_when_source_missing(self, tmp_path):
        src = tmp_path / "missing.tmp"
        dst = tmp_path / "destination.mp3"

        with pytest.raises((FileNotFoundError, RuntimeError)):
            await _replace_with_retry(str(src), str(dst), retries=1)
