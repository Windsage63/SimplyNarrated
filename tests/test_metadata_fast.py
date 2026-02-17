"""
Unit tests for update_m4a_metadata_fast() — the Mutagen in-place metadata path.
"""

import os
import pytest
from src.core.encoder import (
    update_m4a_metadata_fast,
    read_m4a_metadata,
)


# ------------------------------------------------------------------
# Test 1 — Edit title only  (Scenario 1)
# ------------------------------------------------------------------
def test_update_title_only(small_m4a_copy):
    before = read_m4a_metadata(small_m4a_copy)
    assert before["title"] == "Original Title"

    update_m4a_metadata_fast(small_m4a_copy, title="New Title")

    after = read_m4a_metadata(small_m4a_copy)
    assert after["title"] == "New Title"
    assert after["author"] == before["author"]  # unchanged
    assert len(after["chapters"]) == len(before["chapters"])


# ------------------------------------------------------------------
# Test 2 — Edit author only  (Scenario 2)
# ------------------------------------------------------------------
def test_update_author_only(small_m4a_copy):
    before = read_m4a_metadata(small_m4a_copy)

    update_m4a_metadata_fast(small_m4a_copy, author="New Author")

    after = read_m4a_metadata(small_m4a_copy)
    assert after["author"] == "New Author"
    assert after["title"] == before["title"]  # unchanged


# ------------------------------------------------------------------
# Test 3 — Edit title + author  (Scenario 3)
# ------------------------------------------------------------------
def test_update_title_and_author(small_m4a_copy):
    update_m4a_metadata_fast(small_m4a_copy, title="Both Title", author="Both Author")

    after = read_m4a_metadata(small_m4a_copy)
    assert after["title"] == "Both Title"
    assert after["author"] == "Both Author"
    assert len(after["chapters"]) == 2  # chapters intact


# ------------------------------------------------------------------
# Test 4 — Upload cover only  (Scenario 4)
# ------------------------------------------------------------------
def test_update_cover_only(small_m4a_copy, sample_cover):
    update_m4a_metadata_fast(small_m4a_copy, cover_path=sample_cover)

    # Verify cover is embedded by reading with mutagen directly
    from mutagen.mp4 import MP4

    audio = MP4(small_m4a_copy)
    assert "covr" in audio.tags
    assert len(audio.tags["covr"]) == 1
    assert len(audio.tags["covr"][0]) > 0  # has actual image bytes


# ------------------------------------------------------------------
# Test 5 — Edit title + upload cover  (Scenario 5)
# ------------------------------------------------------------------
def test_update_title_and_cover(small_m4a_copy, sample_cover):
    update_m4a_metadata_fast(
        small_m4a_copy, title="Cover Title", cover_path=sample_cover
    )

    after = read_m4a_metadata(small_m4a_copy)
    assert after["title"] == "Cover Title"

    from mutagen.mp4 import MP4

    audio = MP4(small_m4a_copy)
    assert "covr" in audio.tags


# ------------------------------------------------------------------
# Test 6 — Audio integrity after update  (Scenario 6)
# ------------------------------------------------------------------
def test_audio_integrity_after_update(small_m4a_copy):
    before = read_m4a_metadata(small_m4a_copy)
    original_size = os.path.getsize(small_m4a_copy)

    update_m4a_metadata_fast(
        small_m4a_copy, title="Integrity Test", author="Integrity Author"
    )

    after = read_m4a_metadata(small_m4a_copy)

    # Duration must be preserved exactly
    assert abs(after["duration_seconds"] - before["duration_seconds"]) < 0.1

    # File size should be close (metadata-only change, no re-encode)
    new_size = os.path.getsize(small_m4a_copy)
    ratio = new_size / original_size
    # Tolerance is generous because metadata on a tiny 1s fixture is
    # proportionally large; for real files the ratio would be ~1.0.
    assert 0.5 < ratio < 2.0, (
        f"File size changed too much: {original_size} -> {new_size}"
    )


# ------------------------------------------------------------------
# Test 7 — Metadata persists across reads  (Scenario 7)
# ------------------------------------------------------------------
def test_metadata_persists_across_reads(small_m4a_copy):
    # Write 1
    update_m4a_metadata_fast(small_m4a_copy, title="First Write")
    read1 = read_m4a_metadata(small_m4a_copy)
    assert read1["title"] == "First Write"

    # Write 2
    update_m4a_metadata_fast(small_m4a_copy, author="Second Write")
    read2 = read_m4a_metadata(small_m4a_copy)
    assert read2["title"] == "First Write"  # still from write 1
    assert read2["author"] == "Second Write"


# ------------------------------------------------------------------
# Test 8 — SNMETA round-trip  (Scenario 8)
# ------------------------------------------------------------------
def test_snmeta_roundtrip(small_m4a_copy):
    custom_meta = {
        "SIMPLYNARRATED_ID": "test-uuid-1234",
        "SIMPLYNARRATED_CREATED_AT": "2026-02-15T10:30:00",
        "SIMPLYNARRATED_ORIGINAL_FILENAME": "my_book.pdf",
        "SIMPLYNARRATED_TRANSCRIPT_PATH": "transcript.txt",
    }

    update_m4a_metadata_fast(
        small_m4a_copy,
        title="SNMETA Test",
        custom_metadata=custom_meta,
    )

    after = read_m4a_metadata(small_m4a_copy)
    assert after["id"] == "test-uuid-1234"
    assert after["created_at"] == "2026-02-15T10:30:00"
    assert after["original_filename"] == "my_book.pdf"
    assert after["transcript_path"] == "transcript.txt"


# ------------------------------------------------------------------
# Test 9 — Chapters preserved  (Scenario 6 chapter sub-check)
# ------------------------------------------------------------------
def test_chapters_preserved(small_m4a_copy):
    before = read_m4a_metadata(small_m4a_copy)
    assert len(before["chapters"]) == 2

    update_m4a_metadata_fast(small_m4a_copy, title="Chapter Preservation")

    after = read_m4a_metadata(small_m4a_copy)
    assert len(after["chapters"]) == len(before["chapters"])

    for b_ch, a_ch in zip(before["chapters"], after["chapters"]):
        assert a_ch["title"] == b_ch["title"]
        assert a_ch["start_seconds"] == b_ch["start_seconds"]
        assert a_ch["end_seconds"] == b_ch["end_seconds"]
        assert a_ch["transcript_start"] == b_ch["transcript_start"]
        assert a_ch["transcript_end"] == b_ch["transcript_end"]


# ------------------------------------------------------------------
# Test 10 — File not found raises
# ------------------------------------------------------------------
def test_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        update_m4a_metadata_fast("/nonexistent/path/audio.m4a", title="Nope")
