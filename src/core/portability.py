"""
@fileoverview SimplyNarrated - Audiobook portability helpers for export/import ZIP archives
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

import copy
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime
from typing import Any, Dict, Tuple

from src.core.library import LibraryManager


ARCHIVE_TYPE = "simplynarrated-audiobook"
ARCHIVE_SCHEMA_VERSION = 1
ARCHIVE_MANIFEST_NAME = "export_manifest.json"
MAX_ARCHIVE_MEMBERS = 500
MAX_ARCHIVE_UNCOMPRESSED_SIZE = 1024 * 1024 * 1024
CHAPTER_AUDIO_PATTERN = re.compile(r"^chapter_\d+\.[A-Za-z0-9]+$")
CHAPTER_TEXT_PATTERN = re.compile(r"^chapter_\d+\.txt$")
WINDOWS_RESERVED_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def sanitize_filename_component(value: str) -> str:
    """Make a value safe for use as a Windows filename component."""
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (value or "").strip())
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    if not sanitized:
        sanitized = "audiobook"

    stem, suffix = os.path.splitext(sanitized)
    if stem.upper() in WINDOWS_RESERVED_BASENAMES:
        stem = f"{stem}_book"
    sanitized = f"{stem}{suffix}"
    return sanitized[:180]


def _is_safe_archive_member(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if not normalized or normalized.startswith("/"):
        return False
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return False
    if re.match(r"^[A-Za-z]:$", parts[0]) or re.match(r"^[A-Za-z]:", parts[0]):
        return False
    return all(part != ".." for part in parts)


def _normalize_archive_members(zf: zipfile.ZipFile) -> Dict[str, zipfile.ZipInfo]:
    members = [info for info in zf.infolist() if not info.is_dir()]
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise ValueError(f"Archive has too many members ({len(members)})")

    total_uncompressed = sum(info.file_size for info in members)
    if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_SIZE:
        raise ValueError("Archive content exceeds size limit")

    normalized_entries: Dict[str, zipfile.ZipInfo] = {}
    parts_list = []
    for info in members:
        if not _is_safe_archive_member(info.filename):
            raise ValueError("Archive contains unsafe member paths")
        parts = [part for part in info.filename.replace("\\", "/").split("/") if part]
        parts_list.append(parts)

    root_prefix = None
    if parts_list and all(len(parts) > 1 for parts in parts_list):
        candidate = parts_list[0][0]
        if all(parts[0] == candidate for parts in parts_list):
            root_prefix = candidate

    for info, parts in zip(members, parts_list):
        relative_parts = parts[1:] if root_prefix else parts
        relative_name = "/".join(relative_parts)
        if relative_name in normalized_entries:
            raise ValueError("Archive contains duplicate file entries")
        normalized_entries[relative_name] = info

    return normalized_entries


def _json_from_archive(zf: zipfile.ZipFile, entries: Dict[str, zipfile.ZipInfo], name: str) -> Dict[str, Any]:
    info = entries.get(name)
    if not info:
        raise ValueError(f"Archive is missing required file: {name}")

    try:
        return json.loads(zf.read(info).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Archive contains invalid JSON in {name}") from exc


def _normalize_book_metadata(metadata: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    normalized = copy.deepcopy(metadata)
    chapters = normalized.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("Book metadata does not contain any chapters")

    selected_files: Dict[str, str] = {}
    normalized_chapters = []
    for chapter in sorted(chapters, key=lambda item: int(item.get("number", 0))):
        chapter_number = int(chapter.get("number", 0))
        if chapter_number < 1:
            raise ValueError("Book metadata contains an invalid chapter number")

        audio_name = sanitize_filename_component(
            os.path.basename(chapter.get("audio_path") or f"chapter_{chapter_number:02d}.mp3")
        )
        text_name = sanitize_filename_component(
            os.path.basename(chapter.get("text_path") or f"chapter_{chapter_number:02d}.txt")
        )

        if not CHAPTER_AUDIO_PATTERN.match(audio_name):
            raise ValueError(f"Unsupported chapter audio filename: {audio_name}")
        if not CHAPTER_TEXT_PATTERN.match(text_name):
            raise ValueError(f"Unsupported chapter text filename: {text_name}")

        chapter["audio_path"] = audio_name
        chapter["text_path"] = text_name
        normalized_chapters.append(chapter)
        selected_files[audio_name] = audio_name
        selected_files[text_name] = text_name

    normalized["chapters"] = normalized_chapters

    source_file = normalized.get("source_file")
    if source_file:
        normalized_source = sanitize_filename_component(os.path.basename(source_file))
        normalized["source_file"] = normalized_source
        selected_files[normalized_source] = normalized_source

    return normalized, selected_files


def _build_archive_manifest(metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "archive_type": ARCHIVE_TYPE,
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "exported_at": datetime.now().isoformat(),
        "app_name": "SimplyNarrated",
        "book_id": metadata.get("id"),
        "title": metadata.get("title"),
        "total_chapters": metadata.get("total_chapters"),
    }


def export_book_archive(library: LibraryManager, book_id: str) -> Tuple[str, str]:
    """Create a portability ZIP for a book and return (path, download_name)."""
    book_dir = library.get_book_dir(book_id)
    metadata_path = os.path.join(book_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError("Book metadata not found")

    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)

    export_metadata, selected_files = _normalize_book_metadata(metadata)
    cover_name = None
    for candidate in ("cover.jpg", "cover.png"):
        candidate_path = os.path.join(book_dir, candidate)
        if os.path.exists(candidate_path):
            cover_name = candidate
            selected_files[candidate] = candidate
            break

    bookmarks_path = os.path.join(book_dir, "bookmarks.json")
    if os.path.exists(bookmarks_path):
        selected_files["bookmarks.json"] = "bookmarks.json"

    root_name = sanitize_filename_component(export_metadata.get("title") or book_id)
    archive_fd, archive_path = tempfile.mkstemp(prefix="simplynarrated-export-", suffix=".zip")
    os.close(archive_fd)

    manifest = _build_archive_manifest(export_metadata)
    if cover_name:
        export_metadata["cover_url"] = f"/api/book/{book_id}/cover"

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"{root_name}/{ARCHIVE_MANIFEST_NAME}",
            json.dumps(manifest, indent=2),
        )
        archive.writestr(
            f"{root_name}/metadata.json",
            json.dumps(export_metadata, indent=2),
        )

        for relative_name in sorted(selected_files):
            source_path = os.path.join(book_dir, relative_name)
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"Missing required export file: {relative_name}")
            archive.write(source_path, arcname=f"{root_name}/{relative_name}")

    download_name = f"{sanitize_filename_component(export_metadata.get('title') or book_id)}.zip"
    return archive_path, download_name


def _write_archive_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, destination_path: str) -> None:
    with zf.open(info, "r") as source, open(destination_path, "wb") as target:
        shutil.copyfileobj(source, target)


def import_book_archive(library: LibraryManager, archive_path: str) -> Dict[str, Any]:
    """Import a portability ZIP into the library and return the resulting book info."""
    try:
        with zipfile.ZipFile(archive_path) as archive:
            entries = _normalize_archive_members(archive)
            manifest = _json_from_archive(archive, entries, ARCHIVE_MANIFEST_NAME)
            if manifest.get("archive_type") != ARCHIVE_TYPE:
                raise ValueError("ZIP is not a SimplyNarrated audiobook archive")
            if int(manifest.get("schema_version", 0)) != ARCHIVE_SCHEMA_VERSION:
                raise ValueError("Unsupported audiobook archive schema version")

            metadata = _json_from_archive(archive, entries, "metadata.json")
            normalized_metadata, selected_files = _normalize_book_metadata(metadata)

            requested_book_id = str(normalized_metadata.get("id") or "")
            id_remapped = False
            if not re.fullmatch(r"^[a-f0-9-]{36}$", requested_book_id):
                requested_book_id = str(uuid.uuid4())
                id_remapped = True

            destination_book_id = requested_book_id
            destination_dir = library.get_book_dir(destination_book_id)
            if os.path.exists(destination_dir):
                destination_book_id = str(uuid.uuid4())
                destination_dir = library.get_book_dir(destination_book_id)
                id_remapped = True

            optional_files = {}
            if normalized_metadata.get("source_file") and normalized_metadata["source_file"] in entries:
                optional_files[normalized_metadata["source_file"]] = normalized_metadata["source_file"]
            else:
                normalized_metadata["source_file"] = None

            cover_name = None
            for candidate in ("cover.jpg", "cover.png"):
                if candidate in entries:
                    cover_name = candidate
                    optional_files[candidate] = candidate
                    break

            if "bookmarks.json" in entries:
                optional_files["bookmarks.json"] = "bookmarks.json"

            required_names = {"metadata.json", *selected_files.keys()}
            missing_required = sorted(name for name in required_names if name != "metadata.json" and name not in entries)
            if missing_required:
                raise ValueError(f"Archive is missing required files: {', '.join(missing_required)}")

            stage_root = tempfile.mkdtemp(prefix="simplynarrated-import-")
            stage_dir = os.path.join(stage_root, destination_book_id)
            os.makedirs(stage_dir, exist_ok=True)

            try:
                for relative_name in sorted({*selected_files.keys(), *optional_files.keys()}):
                    destination_path = os.path.join(stage_dir, relative_name)
                    _write_archive_member(archive, entries[relative_name], destination_path)

                normalized_metadata["id"] = destination_book_id
                normalized_metadata["cover_url"] = (
                    f"/api/book/{destination_book_id}/cover" if cover_name else None
                )
                normalized_metadata["imported_at"] = datetime.now().isoformat()

                metadata_destination = os.path.join(stage_dir, "metadata.json")
                with open(metadata_destination, "w", encoding="utf-8") as metadata_file:
                    json.dump(normalized_metadata, metadata_file, indent=2)

                shutil.move(stage_dir, destination_dir)
            except Exception:
                shutil.rmtree(stage_root, ignore_errors=True)
                raise
            else:
                shutil.rmtree(stage_root, ignore_errors=True)

    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid or corrupt ZIP file") from exc

    return {
        "status": "imported",
        "book_id": destination_book_id,
        "title": normalized_metadata.get("title") or "Imported Audiobook",
        "total_chapters": len(normalized_metadata.get("chapters", [])),
        "id_remapped": id_remapped,
    }