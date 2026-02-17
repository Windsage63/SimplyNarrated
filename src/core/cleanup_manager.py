"""
@fileoverview SimplyNarrated - Cleanup Manager, detects incomplete conversion artifacts and applies user decisions
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
import shutil
import logging
from dataclasses import dataclass

from src.core.job_manager import get_job_manager
from src.core.book_files import find_primary_m4a_path
from src.models.schemas import CleanupDecision

logger = logging.getLogger(__name__)


@dataclass
class CleanupCandidate:
    item_id: str
    item_type: str
    title: str
    details: str
    recommendation: CleanupDecision


class CleanupManager:
    """Scans and resolves incomplete conversion artifacts."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.library_dir = os.path.join(data_dir, "library")

    @staticmethod
    def _has_primary_m4a(folder_path: str) -> bool:
        return find_primary_m4a_path(folder_path) is not None

    @staticmethod
    def _safe_rmtree(path: str) -> bool:
        if not os.path.exists(path):
            return True
        try:
            shutil.rmtree(path)
            return True
        except Exception as exc:
            logger.error("Failed to remove path %s: %s", path, exc)
            return False

    @staticmethod
    def _is_safe_folder_token(token: str) -> bool:
        if not token:
            return False
        if token != os.path.basename(token):
            return False
        if ".." in token:
            return False
        if "/" in token or "\\" in token:
            return False
        return True

    def get_pending_items(self) -> list[CleanupCandidate]:
        candidates: list[CleanupCandidate] = []
        job_manager = get_job_manager()
        jobs = job_manager.list_jobs()
        job_ids = {job.id for job in jobs}

        for job in jobs:
            if job.status.value not in {"failed", "cancelled"}:
                continue
            output_dir = job.output_dir or os.path.join(self.library_dir, job.id)
            if not os.path.isdir(output_dir):
                continue
            if self._has_primary_m4a(output_dir):
                continue

            candidates.append(
                CleanupCandidate(
                    item_id=f"job:{job.id}",
                    item_type="failed_job",
                    title=f"Incomplete conversion: {job.filename}",
                    details=(
                        f"Job {job.id} is {job.status.value} and has no completed audiobook output. "
                        "These files cannot be resumed."
                    ),
                    recommendation=CleanupDecision.DELETE,
                )
            )

            segment_dir = os.path.join(output_dir, "_segments")
            if os.path.isdir(segment_dir):
                candidates.append(
                    CleanupCandidate(
                        item_id=f"segments:{job.id}",
                        item_type="stale_segments",
                        title=f"Temporary segment files for {job.filename}",
                        details="Temporary conversion segment files were left behind and are safe to remove.",
                        recommendation=CleanupDecision.DELETE,
                    )
                )

        if os.path.isdir(self.library_dir):
            for folder_name in os.listdir(self.library_dir):
                folder_path = os.path.join(self.library_dir, folder_name)
                if not os.path.isdir(folder_path):
                    continue

                segment_dir = os.path.join(folder_path, "_segments")
                if os.path.isdir(segment_dir):
                    candidates.append(
                        CleanupCandidate(
                            item_id=f"segments:{folder_name}",
                            item_type="stale_segments",
                            title=f"Temporary segment files in {folder_name}",
                            details="Temporary conversion segment files were left behind and are safe to remove.",
                            recommendation=CleanupDecision.DELETE,
                        )
                    )

                if folder_name in job_ids:
                    continue

                if self._has_primary_m4a(folder_path):
                    continue

                candidates.append(
                    CleanupCandidate(
                        item_id=f"orphan:{folder_name}",
                        item_type="orphan_folder",
                        title=f"Orphaned incomplete folder: {folder_name}",
                        details=(
                            "This folder has no matching job record and no completed audiobook output. "
                            "It is likely leftover failed conversion data."
                        ),
                        recommendation=CleanupDecision.DELETE,
                    )
                )

        deduped: dict[str, CleanupCandidate] = {}
        for item in candidates:
            deduped[item.item_id] = item
        return list(deduped.values())

    def apply_decision(self, item_id: str, decision: CleanupDecision) -> dict:
        if decision == CleanupDecision.KEEP:
            return {
                "status": "kept",
                "item_id": item_id,
                "message": "Item kept. It may be prompted again on next startup.",
            }

        prefix, _, key = item_id.partition(":")
        if not prefix or not key:
            return {"status": "error", "item_id": item_id, "message": "Invalid cleanup item id"}

        if not self._is_safe_folder_token(key):
            return {
                "status": "error",
                "item_id": item_id,
                "message": "Unsafe cleanup item id",
            }

        if prefix == "job":
            folder_path = os.path.join(self.library_dir, key)
            folder_ok = self._safe_rmtree(folder_path)
            job_removed = get_job_manager().remove_job(key)
            if folder_ok:
                return {
                    "status": "deleted",
                    "item_id": item_id,
                    "message": "Incomplete job artifacts deleted.",
                    "job_removed": job_removed,
                }
            return {"status": "error", "item_id": item_id, "message": "Failed to delete incomplete job files"}

        if prefix == "orphan":
            folder_path = os.path.join(self.library_dir, key)
            if self._safe_rmtree(folder_path):
                return {
                    "status": "deleted",
                    "item_id": item_id,
                    "message": "Orphaned folder deleted.",
                }
            return {"status": "error", "item_id": item_id, "message": "Failed to delete orphaned folder"}

        if prefix == "segments":
            folder_path = os.path.join(self.library_dir, key, "_segments")
            if self._safe_rmtree(folder_path):
                return {
                    "status": "deleted",
                    "item_id": item_id,
                    "message": "Temporary segment files deleted.",
                }
            return {
                "status": "error",
                "item_id": item_id,
                "message": "Failed to delete temporary segment files",
            }

        return {"status": "error", "item_id": item_id, "message": "Unsupported cleanup item"}


_cleanup_manager: CleanupManager | None = None


def get_cleanup_manager() -> CleanupManager:
    """Get the global cleanup manager instance."""
    global _cleanup_manager
    if _cleanup_manager is None:
        raise RuntimeError("CleanupManager not initialized")
    return _cleanup_manager


def init_cleanup_manager(data_dir: str) -> CleanupManager:
    """Initialize the global cleanup manager."""
    global _cleanup_manager
    _cleanup_manager = CleanupManager(data_dir)
    return _cleanup_manager
