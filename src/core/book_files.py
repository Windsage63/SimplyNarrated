"""
@fileoverview SimplyNarrated - Shared book file helpers
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

import os
import re


def sanitize_book_filename(title: str, fallback: str) -> str:
    """Return a filesystem-safe book filename stem."""
    candidate = re.sub(r"[\\/:*?\"<>|]+", " ", title or "")
    candidate = re.sub(r"\s+", " ", candidate).strip().strip(".")
    return candidate or fallback


def is_primary_m4a_filename(filename: str) -> bool:
    """Identify production audiobook output files while excluding temp/metadata artifacts."""
    lower = filename.lower()
    if not lower.endswith(".m4a"):
        return False
    if ".metadata." in lower or ".tmp." in lower or lower.endswith(".tmp.m4a"):
        return False
    return True


def find_primary_m4a_path(folder_path: str) -> str | None:
    """Return the newest primary M4A path in a folder, if present."""
    if not os.path.isdir(folder_path):
        return None

    candidates: list[tuple[str, float, str]] = []
    for name in os.listdir(folder_path):
        if not is_primary_m4a_filename(name):
            continue
        path = os.path.join(folder_path, name)
        if not os.path.isfile(path) or os.path.getsize(path) <= 0:
            continue
        candidates.append((name, os.path.getmtime(path), path))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[1], item[0].lower()), reverse=True)
    return candidates[0][2]


def find_cover_path(book_dir: str) -> str | None:
    """Return the canonical cover image path if present."""
    for candidate in ("cover.jpg", "cover.png"):
        path = os.path.join(book_dir, candidate)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    return None
