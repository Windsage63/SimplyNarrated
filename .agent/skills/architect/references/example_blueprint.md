# Example Architectural Blueprint

A comprehensive completed blueprint demonstrating all sections. Use this as a calibration reference for output quality and depth.

## Contents

1. Executive Summary
2. Technical Stack
3. Architectural Overview
4. Core Architectural Decisions (ADR-1 through ADR-4)
5. Component Breakdown
6. Data Architecture
7. API Design
8. Security Architecture
9. Error Handling & Resilience
10. Testing Strategy
11. Performance & Scaling
12. Deployment & Infrastructure
13. Requirements & Acceptance Criteria
14. Implementation Roadmap (4 phases)
15. Risks & Mitigations
16. Open Questions

````markdown
# MediaVault — Architectural Blueprint

## 1. Executive Summary

MediaVault is a self-hosted media management application that organizes, transcodes, and streams personal video collections with automatic metadata enrichment. The architecture prioritizes local-first operation with no cloud dependencies, using a Python backend with SQLite for metadata and filesystem-based media storage.

## 2. Technical Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Vanilla JS SPA + Tailwind CSS | No build step, offline-capable, minimal dependencies |
| Backend | Python 3.12 / FastAPI | Async-native, strong typing, excellent media library ecosystem |
| Database | SQLite (via aiosqlite) | Zero-config, file-portable, sufficient for single-user local app |
| Media Processing | FFmpeg (via ffmpeg-python) | Industry standard, GPU-accelerable, handles all codecs |
| Search | SQLite FTS5 | Built-in full-text search, no external service needed |
| Auth | None (local-only) | Single-user local app; optional API key for LAN access |

## 3. Architectural Overview

### System Context

MediaVault runs as a single process on the user's machine. The FastAPI server serves both the SPA and API endpoints. Media files remain in their original locations on disk — MediaVault indexes them without moving or copying.

### Component Interaction

```markdown
Browser (SPA)
    │
    ▼
FastAPI Server ──► SQLite DB (metadata, search index)
    │
    ├──► File System (original media files)
    ├──► FFmpeg (transcoding pipeline)
    └──► TMDb API (optional metadata enrichment)
```

### Key Architectural Pattern

**Pipeline architecture** for media processing: Scan → Identify → Enrich → Transcode → Index. Each stage is an independent async task that can fail and retry without affecting other stages.

## 4. Core Architectural Decisions

### ADR-1: File-Based Indexing Over Media Import

- **Choice:** Index media in-place on the filesystem rather than importing/copying into a managed directory
- **Rationale:** Users have existing folder structures they want to preserve. Copying terabytes of media is impractical.
- **Trade-offs:** Must handle files being moved/deleted externally. Requires periodic re-scan to detect changes. Cannot guarantee file integrity.

### ADR-2: SQLite Over PostgreSQL

- **Choice:** SQLite with WAL mode for all metadata storage
- **Rationale:** Single-user local app doesn't need concurrent write scalability. SQLite is zero-config, file-portable, and embeds directly. Backup is just copying a file.
- **Trade-offs:** No concurrent write scaling if app ever goes multi-user. Limited to ~1TB practical database size. No built-in replication.

### ADR-3: Background Job Queue Over Synchronous Processing

- **Choice:** Async job queue with file-based persistence for transcoding and metadata enrichment
- **Rationale:** Transcoding is CPU/GPU intensive and long-running. Users need to queue work and check progress. Jobs must survive app restarts.
- **Trade-offs:** More complex state management. Must handle partial failures and cleanup. Job serialization format becomes a compatibility concern.

### ADR-4: Optional External Metadata Over Required Internet

- **Choice:** TMDb API enrichment is optional and gracefully degraded
- **Rationale:** Local-first principle. App must work fully offline. Enrichment is nice-to-have, not essential.
- **Trade-offs:** Metadata quality depends on filename parsing when offline. No poster art without API access.

## 5. Component Breakdown

| Component | Description | Priority | Dependencies |
| --------- | ----------- | -------- | ------------ |
| Media Scanner | Walks filesystem, detects media files by extension/magic bytes | P0 | None |
| Metadata Store | SQLite schema for media records, collections, tags | P0 | None |
| REST API | CRUD for media, collections, job management, streaming | P0 | Scanner, Store |
| SPA Frontend | Browse, search, play media with adaptive streaming | P0 | API |
| Transcode Pipeline | FFmpeg wrapper for format conversion with progress tracking | P1 | Scanner, Store |
| Metadata Enricher | TMDb API integration for titles, descriptions, artwork | P1 | Store |
| Search Engine | FTS5-powered full-text search across all metadata fields | P1 | Store |
| Job Manager | Async queue with persistence, progress tracking, retry logic | P0 | Store |
| Thumbnail Generator | Extracts video thumbnails at configurable intervals | P2 | Scanner, FFmpeg |

## 6. Data Architecture

### Storage Model

- **SQLite database:** `data/mediavault.db` — All metadata, search index, job state
- **Media files:** Remain in original filesystem locations (indexed, not moved)
- **Generated assets:** `data/thumbnails/`, `data/transcoded/` — Output artifacts
- **Configuration:** `data/config.json` — User preferences, scan paths, API keys

### Core Schema

| Table | Purpose | Key Fields |
| ----- | ------- | ---------- |
| `media` | Indexed media files | id, path, hash, title, duration, codec, resolution, size |
| `collections` | User-organized groups | id, name, description, sort_order |
| `collection_media` | Many-to-many join | collection_id, media_id, position |
| `tags` | Freeform labels | id, name |
| `media_tags` | Many-to-many join | media_id, tag_id |
| `jobs` | Processing queue | id, type, status, progress, media_id, config, error |
| `scan_history` | Filesystem scan records | id, path, started_at, completed_at, files_found |

### Data Flow

1. **Scan:** User configures watch directories → Scanner walks filesystem → New media inserted into `media` table
2. **Enrich:** Background job fetches TMDb data → Updates `media` title, description, artwork_url
3. **Transcode:** User requests format conversion → Job queued → FFmpeg processes → Output written to `data/transcoded/`
4. **Stream:** SPA requests media → API checks codec compatibility → Serves original or transcoded version

### Migration Strategy

Schema versioned with integer migrations in `data/migrations/`. On startup, app checks `schema_version` pragma and applies pending migrations sequentially.

## 7. API Design

### Conventions

- REST endpoints under `/api/v1/`
- JSON request/response bodies
- Pagination via `?offset=0&limit=50`
- Errors return `{"detail": "message"}` with appropriate HTTP status

### Key Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/scan` | Trigger filesystem scan |
| GET | `/api/v1/media` | List media with filtering/search |
| GET | `/api/v1/media/{id}` | Get single media metadata |
| GET | `/api/v1/media/{id}/stream` | Stream media file (range requests supported) |
| POST | `/api/v1/media/{id}/transcode` | Queue transcoding job |
| GET/POST | `/api/v1/collections` | List/create collections |
| GET | `/api/v1/jobs` | List active/completed jobs |
| GET | `/api/v1/search?q=` | Full-text search |

## 8. Security Architecture

### Threat Model

- **Local-only by default:** Binds to `127.0.0.1`. No external access unless user explicitly enables LAN mode.
- **LAN mode:** Optional API key authentication via `X-API-Key` header. Key stored hashed in config.
- **Path traversal:** All file operations validate paths are within configured scan directories. Symlinks followed only within allowed roots.
- **Input validation:** Pydantic models validate all API inputs. FFmpeg commands constructed via library API, never string interpolation.
- **No user accounts:** Single-user app. No password storage, session management, or RBAC needed.

### Data Sensitivity

- Media files may contain personal content — no telemetry, no external transmission without explicit user action
- TMDb API key stored in config file with restrictive file permissions

## 9. Error Handling & Resilience

### Failure Modes

| Failure | Detection | Recovery |
| ------- | --------- | -------- |
| Media file deleted externally | Scan detects missing file | Mark as `unavailable` in DB, don't delete metadata |
| FFmpeg transcode fails | Non-zero exit code | Retry once with lower quality preset, then mark job failed |
| TMDb API unreachable | Connection timeout (5s) | Skip enrichment, queue for retry on next scan |
| SQLite locked | OperationalError | WAL mode prevents most locks; retry with backoff for writes |
| Disk full during transcode | OSError | Cleanup partial output, fail job with clear message |

### Job Recovery

Jobs persist to SQLite. On startup, any job in `running` state is reset to `queued` for retry. Failed jobs retain error details for user review.

## 10. Testing Strategy

| Level | Scope | Tools | Coverage Target |
| ----- | ----- | ----- | --------------- |
| Unit | Schema validation, path handling, query building | pytest | Core logic: 90% |
| Integration | API endpoints, database operations | pytest + httpx | All endpoints |
| Media | FFmpeg pipeline with sample files | pytest (slow marker) | Codec matrix |
| E2E | Full scan → enrich → transcode flow | pytest + tmp directories | Critical paths |

### Test Data

- Small sample media files (< 1MB) checked into `tests/fixtures/`
- Large media tests gated behind `@pytest.mark.slow`
- SQLite tests use in-memory databases for speed

## 11. Performance & Scaling

### Expected Load

- Single user, local machine
- Library size: 100 to 50,000 media files
- Concurrent transcoding: limited to CPU/GPU core count

### Optimization Strategy

- **SQLite indexes** on `media.path`, `media.hash`, `tags.name` for fast lookups
- **FTS5** for sub-100ms full-text search across all metadata
- **Streaming:** Range request support for seeking without downloading entire file
- **Thumbnail cache:** Generate once, serve from disk thereafter
- **Transcode queue:** Process sequentially to avoid CPU contention; user can adjust concurrency

### Bottleneck: Large Library Scan

Initial scan of 50,000 files may take minutes. Mitigated by:

- Incremental scan (only check mtime changes)
- Background async operation with progress reporting
- Hash-based dedup to skip already-indexed files

## 12. Deployment & Infrastructure

### Runtime

- Single Python process via uvicorn
- No containers, orchestration, or reverse proxy required for local use
- Optional: systemd unit / Windows service for auto-start

### Distribution

- Embedded Python (portable, no system install required)
- `install.bat` / `install.sh` provisions dependencies
- FFmpeg bundled or detected from PATH

### Environments

| Environment | Purpose | Configuration |
| ----------- | ------- | ------------- |
| Development | Local dev with hot reload | `uvicorn --reload`, SQLite in `data/` |
| Production | User's machine | `uvicorn` (no reload), same SQLite path |
| Testing | CI / local test | In-memory SQLite, sample fixtures |

## 13. Requirements & Acceptance Criteria

### Functional Requirements

- [ ] FR-1: Scan configured directories and index all recognized media files
- [ ] FR-2: Display media library with thumbnail grid and list views
- [ ] FR-3: Stream media files with seeking support in the browser player
- [ ] FR-4: Transcode media to user-selected format with progress tracking
- [ ] FR-5: Search across all metadata fields with sub-second response
- [ ] FR-6: Organize media into user-created collections
- [ ] FR-7: Optionally enrich metadata from TMDb API

### Non-Functional Requirements

- [ ] NFR-1: App starts and is usable within 5 seconds
- [ ] NFR-2: Search returns results within 200ms for libraries up to 50K items
- [ ] NFR-3: All operations work fully offline (except TMDb enrichment)
- [ ] NFR-4: No data leaves the user's machine without explicit action

## 14. Implementation Roadmap

### Phase 1: Core Foundation (P0)

1. **Metadata Store** — SQLite schema, migrations, async access layer
2. **Media Scanner** — Filesystem walker with extension/magic-byte detection
3. **REST API** — CRUD endpoints for media and collections
4. **SPA Shell** — Basic browse and list view

### Phase 2: Playback & Processing (P0-P1)

1. **Media Streaming** — Range-request file serving with codec detection
2. **Job Manager** — Persistent async queue with progress tracking
3. **Transcode Pipeline** — FFmpeg integration with preset management
4. **Player UI** — In-browser video player with adaptive codec handling

### Phase 3: Enrichment & Search (P1)

1. **Search Engine** — FTS5 indexing and search API
2. **Metadata Enricher** — TMDb API integration with offline fallback
3. **Thumbnail Generator** — Video frame extraction and caching

### Phase 4: Polish (P2)

1. **Collection Management UI** — Drag-and-drop organization
2. **Batch Operations** — Multi-select transcode, tag, delete
3. **Settings UI** — Scan paths, API keys, transcode presets

## 15. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| ----------- | ------- | ------------- | ------------ |
| FFmpeg not available on user's system | Medium | High — no transcoding | Bundle FFmpeg or provide clear install instructions; detect on startup |
| Large libraries cause slow initial scan | Medium | Medium — poor first-run UX | Incremental scan, progress bar, background processing |
| SQLite write contention during heavy transcoding | Low | Medium — failed writes | WAL mode, retry with backoff, separate connections for reads/writes |
| Media codec not supported by browser player | Medium | Medium — can't play some files | Detect unsupported codecs, offer transcode to compatible format |
| TMDb API rate limiting | Low | Low — enrichment delayed | Rate limiter in enricher, exponential backoff, queue for retry |

## 16. Open Questions

- [ ] Should we support subtitle extraction and display?
- [ ] What is the maximum practical library size before SQLite becomes a bottleneck?
- [ ] Should transcoded files be stored alongside originals or in a separate managed directory?
- [ ] Do we need watch-mode for auto-scanning when new files appear?
- [ ] Should collections support nested hierarchies or stay flat?

````
