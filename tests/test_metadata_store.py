import threading
import time
from concurrent.futures import ThreadPoolExecutor

from src.core.metadata_store import read_metadata_file, update_metadata_file, write_metadata_file


def test_update_metadata_file_preserves_concurrent_chapter_updates(tmp_path):
    metadata_path = tmp_path / "metadata.json"
    write_metadata_file(
        str(metadata_path),
        {
            "title": "Concurrent Book",
            "chapters": [
                {"number": 1, "duration": "0:00", "completed": False},
                {"number": 2, "duration": "0:00", "completed": False},
            ],
        },
    )

    start_barrier = threading.Barrier(3)

    def worker(chapter_number: int, duration: str) -> None:
        start_barrier.wait()

        def apply_update(metadata):
            for chapter in metadata["chapters"]:
                if chapter["number"] == chapter_number:
                    chapter["duration"] = duration
                    chapter["completed"] = True
                    break
            time.sleep(0.05)

        update_metadata_file(str(metadata_path), apply_update)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(worker, 1, "1:11"),
            executor.submit(worker, 2, "2:22"),
        ]
        start_barrier.wait()
        for future in futures:
            future.result()

    metadata = read_metadata_file(str(metadata_path))
    chapters = {chapter["number"]: chapter for chapter in metadata["chapters"]}

    assert chapters[1]["duration"] == "1:11"
    assert chapters[1]["completed"] is True
    assert chapters[2]["duration"] == "2:22"
    assert chapters[2]["completed"] is True