from __future__ import annotations

import os


def detect_format(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lower().lstrip(".")