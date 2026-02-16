"""
@fileoverview SimplyNarrated - Audio Encoder, Convert raw audio to MP3/WAV and manage chapter files
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
import json
import time
import stat
import ctypes
import subprocess
import tempfile
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class EncoderSettings:
    """Audio encoding settings."""

    format: str = "m4a"
    bitrate: str = "192k"  # 96k (SD), 128k (HD), 320k (Ultra)
    sample_rate: int = 24000
    channels: int = 1


# Quality presets
QUALITY_PRESETS = {
    "sd": EncoderSettings(bitrate="96k"),
    "hd": EncoderSettings(bitrate="128k"),
    "ultra": EncoderSettings(bitrate="320k"),
}


def get_encoder_settings(quality: str = "sd", format: str = "m4a") -> EncoderSettings:
    """Get encoder settings for a quality preset."""
    preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["sd"])
    return EncoderSettings(
        format=format,
        bitrate=preset.bitrate,
        sample_rate=preset.sample_rate,
        channels=preset.channels,
    )


def encode_audio(
    audio: np.ndarray,
    sample_rate: int,
    output_path: str,
    settings: Optional[EncoderSettings] = None,
) -> str:
    """
    Encode audio array to file.

    Args:
        audio: NumPy array of audio samples
        sample_rate: Sample rate of the audio
        output_path: Path to save the encoded file
        settings: Encoder settings

    Returns:
        Path to the saved file
    """
    if settings is None:
        settings = EncoderSettings()

    # Normalize audio to int16 range
    if audio.dtype == np.float32 or audio.dtype == np.float64:
        audio_int = (audio * 32767).astype(np.int16)
    else:
        audio_int = audio.astype(np.int16)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    from pydub import AudioSegment

    audio_segment = AudioSegment(
        audio_int.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,  # 16-bit
        channels=settings.channels,
    )

    export_format = settings.format.lower()
    export_kwargs = {"bitrate": settings.bitrate}

    if export_format in {"m4a", "m4b"}:
        export_format = "ipod"
        export_kwargs["codec"] = "aac"

    audio_segment.export(output_path, format=export_format, **export_kwargs)

    # Verify the file was written successfully
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(
            f"Audio encoding failed: output file is empty at {output_path}"
        )

    return output_path


def _ffmpeg_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace("=", "\\=")
        .replace("\n", "\\n")
    )


def _write_ffmetadata(
    metadata_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: Optional[List[Dict[str, Any]]] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    lines = [";FFMETADATA1"]
    if title:
        lines.append(f"title={_ffmpeg_escape(title)}")
        lines.append(f"album={_ffmpeg_escape(title)}")
    if author:
        lines.append(f"artist={_ffmpeg_escape(author)}")
        lines.append(f"album_artist={_ffmpeg_escape(author)}")

    custom_payload = {
        str(key): value for key, value in (custom_metadata or {}).items() if value is not None
    }
    if custom_payload:
        lines.append(
            f"comment={_ffmpeg_escape('SNMETA:' + json.dumps(custom_payload, separators=(',', ':')))}"
        )

    if chapters:
        lines.append("track=1/1")

    for chapter in chapters or []:
        start_seconds = float(chapter.get("start_seconds", 0.0) or 0.0)
        end_seconds = float(chapter.get("end_seconds", start_seconds) or start_seconds)
        start_ms = max(0, int(start_seconds * 1000))
        end_ms = max(start_ms + 1, int(end_seconds * 1000))
        chapter_number = int(chapter.get("number", 0) or 0)
        chapter_title = chapter.get("title") or f"Chapter {chapter_number}"
        numbered_title = (
            f"{chapter_number:02d} - {chapter_title}" if chapter_number > 0 else chapter_title
        )

        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start_ms}",
                f"END={end_ms}",
                f"title={_ffmpeg_escape(numbered_title)}",
                f"simplynarrated_chapter={chapter_number or 0}",
                f"simplynarrated_transcript_start={int(chapter.get('transcript_start', 0) or 0)}",
                f"simplynarrated_transcript_end={int(chapter.get('transcript_end', 0) or 0)}",
            ]
        )

    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _run_ffmpeg(command: List[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )


def _run_ffprobe(command: List[str]) -> Dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return json.loads(result.stdout or "{}")


def _probe_single_audio_stream(file_path: str) -> Dict[str, Any]:
    data = _run_ffprobe(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a",
            file_path,
        ]
    )

    streams = data.get("streams") or []
    if len(streams) != 1:
        raise RuntimeError(
            f"Expected exactly one audio stream, found {len(streams)}"
        )

    stream = streams[0]
    return {
        "codec_name": str(stream.get("codec_name") or ""),
        "sample_rate": str(stream.get("sample_rate") or ""),
        "channels": int(stream.get("channels") or 0),
        "channel_layout": str(stream.get("channel_layout") or ""),
    }


def _validate_concat_compatibility(segment_paths: List[str]) -> None:
    if not segment_paths:
        raise ValueError("No audio segments provided for m4a muxing")

    reference_stream: Optional[Dict[str, Any]] = None
    reference_path: Optional[str] = None
    comparable_fields = ("codec_name", "sample_rate", "channels", "channel_layout")

    for path in segment_paths:
        if not os.path.exists(path):
            raise RuntimeError(f"Missing segment file: {path}")
        if os.path.getsize(path) == 0:
            raise RuntimeError(f"Empty segment file: {path}")

        try:
            current_stream = _probe_single_audio_stream(path)
        except Exception as e:
            raise RuntimeError(f"Failed to probe segment '{path}': {e}")

        if reference_stream is None:
            reference_stream = current_stream
            reference_path = path
            continue

        mismatches = []
        for field in comparable_fields:
            if current_stream.get(field) != reference_stream.get(field):
                mismatches.append(
                    f"{field}={current_stream.get(field)} (expected {reference_stream.get(field)})"
                )

        if mismatches:
            mismatch_text = ", ".join(mismatches)
            raise RuntimeError(
                "Incompatible segment for concat copy: "
                f"'{path}' differs from '{reference_path}' ({mismatch_text})"
            )


def _replace_with_retries(source_path: str, target_path: str, retries: int = 5, delay: float = 0.25) -> None:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            if os.path.exists(target_path):
                mode = os.stat(target_path).st_mode
                if not (mode & stat.S_IWRITE):
                    os.chmod(target_path, mode | stat.S_IWRITE)
            os.replace(source_path, target_path)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    if last_error:
        raise last_error


def _force_close_file_handles_windows(file_path: str) -> None:
    if os.name != "nt":
        return

    CCH_RM_SESSION_KEY = 32
    CCH_RM_MAX_APP_NAME = 255
    CCH_RM_MAX_SVC_NAME = 63
    ERROR_MORE_DATA = 234
    RmForceShutdown = 0x1

    DWORD = ctypes.c_uint32
    UINT = ctypes.c_uint
    WCHAR_P = ctypes.c_wchar_p
    BOOL = ctypes.c_int

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", DWORD), ("dwHighDateTime", DWORD)]

    class RM_UNIQUE_PROCESS(ctypes.Structure):
        _fields_ = [("dwProcessId", DWORD), ("ProcessStartTime", FILETIME)]

    class RM_PROCESS_INFO(ctypes.Structure):
        _fields_ = [
            ("Process", RM_UNIQUE_PROCESS),
            ("strAppName", ctypes.c_wchar * (CCH_RM_MAX_APP_NAME + 1)),
            ("strServiceShortName", ctypes.c_wchar * (CCH_RM_MAX_SVC_NAME + 1)),
            ("ApplicationType", DWORD),
            ("AppStatus", DWORD),
            ("TSSessionId", DWORD),
            ("bRestartable", BOOL),
        ]

    rstrtmgr = ctypes.WinDLL("rstrtmgr")

    RmStartSession = rstrtmgr.RmStartSession
    RmStartSession.argtypes = [ctypes.POINTER(DWORD), DWORD, ctypes.c_wchar_p]
    RmStartSession.restype = DWORD

    RmRegisterResources = rstrtmgr.RmRegisterResources
    RmRegisterResources.argtypes = [
        DWORD,
        UINT,
        ctypes.POINTER(WCHAR_P),
        UINT,
        ctypes.c_void_p,
        UINT,
        ctypes.c_void_p,
    ]
    RmRegisterResources.restype = DWORD

    RmGetList = rstrtmgr.RmGetList
    RmGetList.argtypes = [
        DWORD,
        ctypes.POINTER(UINT),
        ctypes.POINTER(UINT),
        ctypes.POINTER(RM_PROCESS_INFO),
        ctypes.POINTER(DWORD),
    ]
    RmGetList.restype = DWORD

    RmShutdown = rstrtmgr.RmShutdown
    RmShutdown.argtypes = [DWORD, ctypes.c_ulong, ctypes.c_void_p]
    RmShutdown.restype = DWORD

    RmEndSession = rstrtmgr.RmEndSession
    RmEndSession.argtypes = [DWORD]
    RmEndSession.restype = DWORD

    session = DWORD(0)
    key_buffer = ctypes.create_unicode_buffer(CCH_RM_SESSION_KEY + 1)

    result = RmStartSession(ctypes.byref(session), 0, key_buffer)
    if result != 0:
        return

    try:
        files = (WCHAR_P * 1)(os.path.abspath(file_path))
        result = RmRegisterResources(session, 1, files, 0, None, 0, None)
        if result != 0:
            return

        needed = UINT(0)
        count = UINT(0)
        reasons = DWORD(0)
        result = RmGetList(session, ctypes.byref(needed), ctypes.byref(count), None, ctypes.byref(reasons))

        if result == ERROR_MORE_DATA and needed.value > 0:
            info_array = (RM_PROCESS_INFO * needed.value)()
            count = UINT(needed.value)
            result = RmGetList(
                session,
                ctypes.byref(needed),
                ctypes.byref(count),
                info_array,
                ctypes.byref(reasons),
            )
            if result == 0 and count.value > 0:
                current_pid = os.getpid()
                has_external_lockers = any(
                    int(info.Process.dwProcessId) != current_pid for info in info_array[: count.value]
                )
                if has_external_lockers:
                    RmShutdown(session, RmForceShutdown, None)
    finally:
        RmEndSession(session)


def _normalize_tags(raw_tags: Optional[Dict[str, Any]]) -> Dict[str, str]:
    tags: Dict[str, str] = {}
    for key, value in (raw_tags or {}).items():
        if value is None:
            continue
        tags[str(key).lower()] = str(value)
    return tags


def read_m4a_metadata(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    data = _run_ffprobe(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_chapters",
            file_path,
        ]
    )

    fmt = data.get("format", {})
    tags = _normalize_tags(fmt.get("tags"))
    custom_payload: Dict[str, Any] = {}
    comment = tags.get("comment") or ""
    if comment.startswith("SNMETA:"):
        try:
            custom_payload = json.loads(comment[len("SNMETA:") :])
        except Exception:
            custom_payload = {}

    custom_tags = {str(key).lower(): value for key, value in custom_payload.items()}
    duration_seconds = float(fmt.get("duration", 0.0) or 0.0)
    title = tags.get("title") or os.path.splitext(os.path.basename(file_path))[0]
    author = tags.get("artist") or tags.get("album_artist") or None

    chapters: List[Dict[str, Any]] = []
    for idx, chapter in enumerate(data.get("chapters", []), start=1):
        chapter_tags = _normalize_tags(chapter.get("tags"))
        chapter_title = chapter_tags.get("title") or f"Chapter {idx}"
        if " - " in chapter_title and chapter_title.split(" - ", 1)[0].isdigit():
            chapter_title = chapter_title.split(" - ", 1)[1]
        start_seconds = float(chapter.get("start_time", 0.0) or 0.0)
        end_seconds = float(chapter.get("end_time", start_seconds) or start_seconds)
        transcript_start = int(chapter_tags.get("simplynarrated_transcript_start", 0) or 0)
        transcript_end = int(chapter_tags.get("simplynarrated_transcript_end", 0) or 0)
        chapter_number = int(chapter_tags.get("simplynarrated_chapter", idx) or idx)
        chapters.append(
            {
                "number": chapter_number,
                "title": chapter_title,
                "duration": format_duration(max(0.0, end_seconds - start_seconds)),
                "start_seconds": round(start_seconds, 3),
                "end_seconds": round(end_seconds, 3),
                "transcript_start": transcript_start,
                "transcript_end": transcript_end,
                "completed": True,
            }
        )

    return {
        "title": title,
        "author": author,
        "album": tags.get("album") or title,
        "duration_seconds": duration_seconds,
        "total_duration": format_duration(duration_seconds),
        "created_at": custom_tags.get("simplynarrated_created_at"),
        "original_filename": custom_tags.get("simplynarrated_original_filename"),
        "transcript_path": custom_tags.get("simplynarrated_transcript_path") or "transcript.txt",
        "id": custom_tags.get("simplynarrated_id"),
        "voice": custom_tags.get("simplynarrated_voice"),
        "quality": custom_tags.get("simplynarrated_quality"),
        "chapters": chapters,
    }


def mux_m4a_from_segments(
    segment_paths: List[str],
    output_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: List[Dict[str, Any]],
    cover_path: Optional[str] = None,
    bitrate: str = "192k",
    custom_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    copy_precheck_error: Optional[Exception] = None
    try:
        _validate_concat_compatibility(segment_paths)
    except Exception as e:
        copy_precheck_error = e

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        concat_list_path = os.path.join(temp_dir, "concat.txt")
        metadata_path = os.path.join(temp_dir, "metadata.txt")

        with open(concat_list_path, "w", encoding="utf-8") as f:
            for path in segment_paths:
                normalized = os.path.abspath(path).replace("\\", "/")
                normalized = normalized.replace("'", "'\\''")
                f.write(f"file '{normalized}'\n")

        _write_ffmetadata(metadata_path, title, author, chapters, custom_metadata)

        command_base = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-f",
            "ffmetadata",
            "-i",
            metadata_path,
        ]

        if cover_path and os.path.exists(cover_path):
            command_base.extend(
                [
                    "-i",
                    cover_path,
                    "-map",
                    "2:v",
                    "-c:v",
                    "mjpeg",
                    "-disposition:v:0",
                    "attached_pic",
                ]
            )

        stream_map_flags = [
            "-map",
            "0:a",
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
        ]

        copy_error: Optional[Exception] = copy_precheck_error
        if copy_precheck_error is None:
            copy_command = command_base + stream_map_flags + [
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                output_path,
            ]

            try:
                _run_ffmpeg(copy_command)
            except Exception as e:
                copy_error = e

        if copy_error is not None:
            reencode_command = command_base + stream_map_flags + [
                "-c:a",
                "aac",
                "-b:a",
                bitrate,
                "-movflags",
                "+faststart",
                output_path,
            ]
            try:
                _run_ffmpeg(reencode_command)
            except Exception as reencode_error:
                raise RuntimeError(
                    "M4A muxing failed. "
                    f"Concat copy error: {copy_error}. "
                    f"Fallback AAC re-encode error: {reencode_error}"
                )

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"M4A muxing failed: output file is empty at {output_path}")

    return output_path


def update_m4a_metadata(
    file_path: str,
    title: Optional[str],
    author: Optional[str],
    chapters: Optional[List[Dict[str, Any]]] = None,
    cover_path: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
    replace_retries: int = 5,
    retry_delay_seconds: float = 0.25,
) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    output_tmp = f"{file_path}.tmp.metadata"
    if os.path.exists(output_tmp):
        os.remove(output_tmp)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = os.path.join(temp_dir, "metadata.txt")
            _write_ffmetadata(metadata_path, title, author, chapters, custom_metadata)

            command = [
                "ffmpeg",
                "-y",
                "-i",
                file_path,
                "-f",
                "ffmetadata",
                "-i",
                metadata_path,
            ]

            if cover_path and os.path.exists(cover_path):
                command.extend(
                    [
                        "-i",
                        cover_path,
                        "-map",
                        "2:v",
                        "-c:v",
                        "mjpeg",
                        "-disposition:v:0",
                        "attached_pic",
                    ]
                )

            command.extend(
                [
                    "-map",
                    "0:a",
                    "-map_metadata",
                    "1",
                    "-map_chapters",
                    "1",
                    "-c:a",
                    "copy",
                    "-f",
                    "mp4",
                ]
            )

            command.append(output_tmp)
            _run_ffmpeg(command)

        try:
            _replace_with_retries(
                source_path=output_tmp,
                target_path=file_path,
                retries=replace_retries,
                delay=retry_delay_seconds,
            )
        except PermissionError:
            _force_close_file_handles_windows(file_path)
            time.sleep(retry_delay_seconds)
            _replace_with_retries(
                source_path=output_tmp,
                target_path=file_path,
                retries=replace_retries,
                delay=retry_delay_seconds,
            )
        return file_path
    except Exception:
        if os.path.exists(output_tmp):
            try:
                os.remove(output_tmp)
            except OSError:
                pass
        raise
def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
