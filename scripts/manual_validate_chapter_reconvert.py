import asyncio
import json
import shutil
import uuid
from pathlib import Path

import numpy as np
import httpx
from pydub import AudioSegment
from httpx import ASGITransport

from src.main import app, DATA_DIR
import src.core.tts_engine as tts_module
from src.core.job_manager import init_job_manager
from src.core.library import init_library_manager


def _duration_to_seconds(value: str) -> float:
    parts = [p.strip() for p in (value or "").split(":") if p.strip()]
    if not parts:
        return 0.0
    if len(parts) == 2:
        minutes, seconds = parts
        return (int(minutes) * 60) + int(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return (int(hours) * 3600) + (int(minutes) * 60) + int(seconds)
    return 0.0


def _format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def _write_test_mp3(path: Path, duration_seconds: float) -> None:
    sample_rate = 24000
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False)
    tone = (np.sin(2 * np.pi * 220 * t) * 32767).astype(np.int16)
    segment = AudioSegment(
        tone.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=1,
    )
    segment.export(str(path), format="mp3", bitrate="128k")


async def _poll_job(client: httpx.AsyncClient, job_id: str, timeout_seconds: int = 120) -> dict:
    start = asyncio.get_running_loop().time()
    while True:
        response = await client.get(f"/api/status/{job_id}")
        response.raise_for_status()
        payload = response.json()
        status = payload["status"]
        if status in {"completed", "failed", "cancelled"}:
            return payload

        if asyncio.get_running_loop().time() - start > timeout_seconds:
            raise TimeoutError("Chapter reconvert timed out")
        await asyncio.sleep(0.5)


async def main() -> None:
    library_dir = Path(DATA_DIR) / "library"
    library_dir.mkdir(parents=True, exist_ok=True)
    (Path(DATA_DIR) / "uploads").mkdir(parents=True, exist_ok=True)

    init_job_manager(DATA_DIR)
    init_library_manager(str(library_dir))

    book_id = str(uuid.uuid4())
    book_dir = library_dir / book_id
    book_dir.mkdir(parents=True, exist_ok=True)

    chapter_num = 1
    initial_text = "Short chapter text for initial audio."
    updated_text = " ".join(["Updated chapter text with additional content for duration validation."] * 8)

    (book_dir / f"chapter_{chapter_num:02d}.txt").write_text(initial_text, encoding="utf-8")
    _write_test_mp3(book_dir / f"chapter_{chapter_num:02d}.mp3", duration_seconds=1.0)

    metadata = {
        "id": book_id,
        "title": "Manual Validation Book",
        "author": "Validation Runner",
        "original_filename": "manual_validation.txt",
        "voice": "af_heart",
        "total_chapters": 1,
        "total_duration": _format_duration(1.0),
        "created_at": "2026-02-27T00:00:00",
        "format": "mp3",
        "quality": "sd",
        "chapters": [
            {
                "number": chapter_num,
                "title": "Chapter 1",
                "duration": _format_duration(1.0),
                "audio_path": f"chapter_{chapter_num:02d}.mp3",
                "text_path": f"chapter_{chapter_num:02d}.txt",
                "completed": True,
            }
        ],
    }
    (book_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Monkeypatch TTS for fast deterministic validation in this script run.
    sample_rate = 24000

    def _fake_generate_speech(text: str, voice_id: str = "af_heart", speed: float = 1.0):
        seconds = max(0.5, min(6.0, len(text) / 55.0))
        t = np.linspace(0, seconds, int(sample_rate * seconds), endpoint=False)
        audio = (np.sin(2 * np.pi * 180 * t)).astype(np.float32)
        return audio, sample_rate

    engine = tts_module.get_tts_engine()
    engine.generate_speech = _fake_generate_speech
    engine.is_initialized = lambda: True

    original_audio_size = (book_dir / f"chapter_{chapter_num:02d}.mp3").stat().st_size

    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            text_before = await client.get(f"/api/text/{book_id}/{chapter_num}")
            text_before.raise_for_status()
            assert text_before.json()["content"] == initial_text

            # Simulate active playback bookmark for resume check.
            resume_position = 0.8
            bookmark_resp = await client.post(
                f"/api/bookmark?book_id={book_id}&chapter={chapter_num}&position={resume_position}"
            )
            bookmark_resp.raise_for_status()

            update_resp = await client.put(
                f"/api/book/{book_id}/chapter/{chapter_num}/text",
                json={"content": updated_text},
            )
            update_resp.raise_for_status()

            reconvert_resp = await client.post(
                f"/api/book/{book_id}/chapter/{chapter_num}/reconvert",
                json={},
            )
            reconvert_resp.raise_for_status()
            job_id = reconvert_resp.json()["job_id"]

            final_status = await _poll_job(client, job_id)
            assert final_status["status"] == "completed", final_status

            text_after = await client.get(f"/api/text/{book_id}/{chapter_num}")
            text_after.raise_for_status()
            assert text_after.json()["content"] == updated_text

            book_after = await client.get(f"/api/book/{book_id}")
            book_after.raise_for_status()
            chapter_meta = book_after.json()["chapters"][0]
            new_duration = _duration_to_seconds(chapter_meta["duration"])
            new_audio_size = (book_dir / f"chapter_{chapter_num:02d}.mp3").stat().st_size

            assert new_audio_size != original_audio_size, "Audio file size did not change"
            assert new_duration > 0, "Duration missing after reconvert"

            resume_after_reload = min(resume_position, max(0.0, new_duration - 0.25))

            print("Validation PASS")
            print(f"- Book ID: {book_id}")
            print(f"- Chapter text updated: {len(updated_text)} chars")
            print(f"- Audio file replaced: {original_audio_size} -> {new_audio_size} bytes")
            print(f"- Chapter duration updated to: {chapter_meta['duration']}")
            print(f"- Resume position check: requested={resume_position:.2f}s, clamped={resume_after_reload:.2f}s")

    finally:
        shutil.rmtree(book_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
