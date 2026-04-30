from __future__ import annotations

import json
import os
from typing import Any, Dict


def write_parser_artifacts(output_dir: str, cleaned_text: str, report_payload: Dict[str, Any]) -> None:
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "source.cleaned.txt"), "w", encoding="utf-8") as cleaned_file:
        cleaned_file.write(cleaned_text)

    with open(os.path.join(output_dir, "parse-report.json"), "w", encoding="utf-8") as report_file:
        json.dump(report_payload, report_file, indent=2)