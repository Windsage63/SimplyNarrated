from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Any, Callable, Dict, TypeVar


T = TypeVar("T")

_metadata_locks: Dict[str, threading.Lock] = {}
_metadata_locks_guard = threading.Lock()


def read_metadata_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as metadata_file:
        return json.load(metadata_file)


def write_metadata_file(path: str, payload: Dict[str, Any]) -> None:
    with _get_metadata_lock(path):
        _write_metadata_file_unlocked(path, payload)


def update_metadata_file(path: str, updater: Callable[[Dict[str, Any]], T]) -> T:
    with _get_metadata_lock(path):
        metadata = read_metadata_file(path)
        result = updater(metadata)
        _write_metadata_file_unlocked(path, metadata)
        return result


def _get_metadata_lock(path: str) -> threading.Lock:
    normalized_path = os.path.abspath(path)
    with _metadata_locks_guard:
        lock = _metadata_locks.get(normalized_path)
        if lock is None:
            lock = threading.Lock()
            _metadata_locks[normalized_path] = lock
        return lock


def _write_metadata_file_unlocked(path: str, payload: Dict[str, Any]) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    file_descriptor, temp_path = tempfile.mkstemp(
        dir=directory,
        prefix=f"{os.path.basename(path)}.",
        suffix=".tmp",
    )

    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as metadata_file:
            json.dump(payload, metadata_file, indent=2, default=str)
            metadata_file.flush()
            os.fsync(metadata_file.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)