"""
@fileoverview SimplyNarrated - Pydantic schemas for API requests and responses
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

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class AudioQuality(str, Enum):
    """Audio output quality options."""

    SD = "sd"  # Standard (96 kbps)
    HD = "hd"  # High Definition (128 kbps)
    ULTRA = "ultra"  # Ultra (320 kbps)


class JobStatus(str, Enum):
    """Conversion job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CleanupDecision(str, Enum):
    """User decision for a cleanup candidate."""

    DELETE = "delete"
    KEEP = "keep"


# --- Request Schemas ---


class GenerateRequest(BaseModel):
    """Request to start audiobook generation."""

    job_id: str
    narrator_voice: str = Field(default="af_heart", description="Voice for narration")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Playback speed")
    quality: AudioQuality = Field(default=AudioQuality.SD)
    remove_square_bracket_numbers: bool = Field(
        default=False, description="Remove [N] footnote references from text"
    )
    remove_paren_numbers: bool = Field(
        default=False, description="Remove (N) footnote references from text"
    )

class UpdateMetadataRequest(BaseModel):
    """Request to update book metadata."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    author: Optional[str] = Field(default=None, max_length=500)


class CleanupDecisionRequest(BaseModel):
    """Request to apply a cleanup decision for a pending item."""

    item_id: str
    decision: CleanupDecision


# --- Response Schemas ---


class UploadResponse(BaseModel):
    """Response from file upload."""

    job_id: str
    filename: str
    file_size: int
    estimated_time: Optional[str] = None
    chapters_detected: int = 0


class ActivityLogEntry(BaseModel):
    """Single entry in the activity log."""

    timestamp: datetime
    message: str
    status: str = "info"  # info, success, warning, error


class StatusResponse(BaseModel):
    """Response for job status check."""

    job_id: str
    status: JobStatus
    progress: float = Field(ge=0, le=100, description="Progress percentage")
    current_chapter: int = 0
    total_chapters: int = 0
    time_remaining: Optional[str] = None
    processing_rate: Optional[str] = None
    activity_log: List[ActivityLogEntry] = []


class VoiceInfo(BaseModel):
    """Information about an available voice."""

    id: str
    name: str
    description: str
    sample_url: Optional[str] = None
    gender: str = "neutral"


class VoicesResponse(BaseModel):
    """Response listing available voices."""

    voices: List[VoiceInfo]
    total: int


class ChapterInfo(BaseModel):
    """Information about a book chapter."""

    number: int
    title: str
    duration: Optional[str] = None
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    transcript_start: Optional[int] = None
    transcript_end: Optional[int] = None
    completed: bool = False


class BookInfo(BaseModel):
    """Information about a completed audiobook."""

    id: str
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    total_chapters: int
    total_duration: Optional[str] = None
    created_at: datetime
    original_filename: Optional[str] = None
    book_file: Optional[str] = None
    transcript_path: Optional[str] = None
    chapters: List[ChapterInfo] = []


class LibraryResponse(BaseModel):
    """Response for library listing."""

    books: List[BookInfo]
    total: int
    in_progress: int = 0


class CleanupItem(BaseModel):
    """A pending cleanup candidate surfaced at startup."""

    item_id: str
    item_type: str
    title: str
    details: str
    recommendation: CleanupDecision


class CleanupPendingResponse(BaseModel):
    """Pending cleanup items requiring user decision."""

    items: List[CleanupItem]
    total: int
