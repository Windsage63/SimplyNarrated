# SimplyNarrated - Architectural Blueprint

> **Text-to-Audiobook Conversion Application**
> Using Kokoro-82M TTS with FastAPI Backend

## 1. Executive Summary

SimplyNarrated is a local web application that converts books and text documents (`.txt`, `.md`, `.epub`, `.pdf`) into audiobooks saved as MP3 chapter files. Designed for non-technical users, it provides a polished multi-page interface with a landing page, file upload/configuration screen, conversion progress tracker, audiobook player, and user dashboard. The system uses the Kokoro-82M model running locally on GPU for high-quality, expressive speech synthesis.

## 2. Technical Stack

| Layer | Technology | Rationale |
| ----- | ---------- | --------- |
| **Frontend** | HTML/TailwindCSS/JavaScript | Modern dark-mode UI from Stitch designs |
| **Backend** | Python 3.12 / FastAPI | Modern async framework, auto-generated API docs |
| **TTS Model** | Kokoro-82M (82M) | Apache 2.0 license, high-quality, lightweight, low VRAM |
| **Audio** | pydub + ffmpeg | MP3/WAV encoding and audio manipulation |
| **File Parsing** | ebooklib, PyMuPDF, markdown | EPUB, PDF, and Markdown parsing |
| **Local Server** | Uvicorn | ASGI server for FastAPI |
| **Icons** | Material Symbols Outlined | Google icon font from Stitch designs |
| **Typography** | Inter (Google Fonts) | Clean, professional font family |

## 3. Core Architectural Decisions

### Decision 1: Local-First Architecture

- **Choice:** All processing runs on user's local machine
- **Rationale:** Privacy-focused, no cloud costs, works offline after model download
- **Trade-offs:** Requires GPU (or slower CPU inference), user must install Python and PyTorch

### Decision 2: Chapter-Based Output

- **Choice:** Separate MP3 file per chapter/chunk (≤4000 words each)
- **Rationale:** Easier to navigate, resume listening, smaller file sizes for processing
- **Trade-offs:** Multiple files to manage vs. single concatenated audiobook

### Decision 3: Single Voice System

- **Choice:** Users select one narrator voice
- **Rationale:** Simpler to implement and use

### Decision 4: Smart Chunking Strategy

- **Choice:** Hybrid approach — prefer natural breaks (chapters, headings), fall back to word count
- **Rationale:** Preserves semantic coherence, respects document structure
- **Trade-offs:** More complex parsing logic, edge cases with unstructured text

### Decision 5: Multi-Page SPA Architecture (NEW)

- **Choice:** 5 distinct views managed via JavaScript routing
- **Rationale:** Stitch UI designs show comprehensive user experience beyond basic converter
- **Trade-offs:** More complex frontend, requires state management

### Decision 6: File-Based Persistence

- **Choice:** All metadata and user data stored in JSON files within the `data/` directory.
- **Rationale:** Simplicity, portability, and zero-dependency database setup.
- **Constraint:** No SQLite or other database engines are desired. Every data point must be traceable to a JSON file.

## 4. UI Screens (From Stitch Designs)

| Screen | Purpose | Key Features |
| ------ | ------- | ------------ |
| **Landing Page** | Marketing/intro page | Hero section, 3-step process, feature cards, CTA |
| **File Upload & Config** | Main conversion setup | Drag-drop upload, voice cards with preview, audio settings (speed, quality, format) |
| **Conversion Progress** | Processing feedback | Circular progress indicator, activity log, time/rate stats, cancel option |
| **Audiobook Player** | Built-in playback | Book cover display, play/pause/skip controls, chapter sidebar, progress scrubber, bookmarks |
| **User Dashboard** | Library management | Conversion queue, book library grid, search, navigation sidebar |

### Design System (From Stitch)

```css
/* Color Palette */
--primary: #137fec;          /* Blue accent */
--background-light: #f6f7f8;
--background-dark: #101922;  /* Dark mode default */

/* Typography */
font-family: 'Inter', sans-serif;

/* Effects */
- Glassmorphism (backdrop-blur-md)
- Rounded corners (0.25rem to full)
- Shadow effects with primary color tints
- Dark mode by default
```

## 5. Component Breakdown

| Component | Description | Priority |
| --------- | ----------- | -------- |
| **File Parser** | Extract and normalize text from TXT/MD/EPUB/PDF | P0 |
| **Text Chunker** | Split text into ≤4000 word segments at natural breaks | P0 |
| **Dialogue Detector** | Identify quoted speech for voice switching | P0 |
| **TTS Engine** | Kokoro-82M wrapper with voice selection | P0 |
| **Audio Encoder** | Convert raw audio to MP3/WAV, save chapters | P0 |
| **REST API** | FastAPI endpoints for all operations | P0 |
| **Landing Page UI** | Marketing page with feature highlights | P1 |
| **Upload/Config UI** | File upload, voice selection, audio settings | P0 |
| **Progress UI** | Circular progress, activity log, stats | P0 |
| **Player UI** | Built-in audiobook player with chapters | P1 |
| **Dashboard UI** | Library management, conversion queue | P1 |

## 6. System Design

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Web Browser (SPA)                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐  │
│  │ Landing Page│ │Upload/Config│ │ Progress │ │ Player  │ │  Dashboard   │  │
│  └──────┬──────┘ └──────┬──────┘ └────┬─────┘ └────┬────┘ └──────┬───────┘  │
└─────────┼───────────────┼─────────────┼────────────┼─────────────┼──────────┘
          │               │             │            │             │
          └───────────────┴──────┬──────┴────────────┴─────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend (Python)                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ POST /api/upload      - Accept file, return job_id                     │ │
│  │ POST /api/generate    - Start TTS with config (voice, speed, quality)  │ │
│  │ GET  /api/status/:id  - Return progress, activity log, stats           │ │
│  │ POST /api/cancel/:id  - Cancel in-progress conversion                  │ │
│  │ GET  /api/voices      - List available voices with preview samples     │ │
│  │ GET  /api/library     - Get user's audiobook library                   │ │
│  │ GET  /api/book/:id    - Get book details and chapters                  │ │
│  │ GET  /api/audio/:id/:chapter - Stream/download chapter audio           │ │
│  │ POST /api/bookmark    - Save playback bookmark                         │ │
│  │ GET  /api/bookmark/:id - Get playback bookmark                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│  ┌───────────┐  ┌─────────────────┴─────────────────┐  ┌─────────────────┐  │
│  │File Parser│─▶│       Text Chunker                │─▶│Dialogue Detector│  │
│  └───────────┘  └───────────────────────────────────┘  └────────┬────────┘  │
│                                                                  │           │
│  ┌───────────────────────────────────────────────────────────────┴────────┐ │
│  │                      TTS Engine (Kokoro-82M)                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐               │ │
│  │  │Voice Manager│  │GPU Inference│  │ Audio Encoder    │               │ │
│  │  └─────────────┘  └─────────────┘  └──────────────────┘               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│  ┌─────────────────────────────────┴───────────────────────────────────────┐│
│  │                     File-Based Data Repository (data/)                   ││
│  │  - library/{book_id}/metadata.json  (title, author, chapters, duration) ││
│  │  - library/{book_id}/chapter_XX.mp3 (audio files)                        ││
│  │  - library/{book_id}/bookmark.json  (chapter, position, timestamp)       ││
│  │  - uploads/ (temporary uploaded files)                                   ││
│  └──────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  data/                  │
                    │  ├─ library/            │
                    │  │  └─ {book_id}/       │
                    │  │     ├─ cover.jpg     │
                    │  │     ├─ chapter_01.mp3│
                    │  │     └─ ...           │
                    │  └─ uploads/            │
                    └─────────────────────────┘
```

### Data Flow

1. **Landing**: User visits landing page → clicks "Start Converting Free"
2. **Upload**: User drags file → POST /api/upload → File saved, job_id returned
3. **Configure**: User picks voice (with preview), speed (0.5x-2.0x), quality (SD/HD/Ultra), format (MP3/WAV)
4. **Generate**: User clicks "Start Conversion" → POST /api/generate with full config
5. **Progress**: Frontend shows circular progress, activity log with phases:
   - Extracting text from file
   - Generating audio for chapters 1-N
   - Finalizing MP3 chapters & metadata
6. **Complete**: Book added to library, user can play immediately or download
7. **Playback**: Built-in player with chapters, bookmarks, speed control, volume

## 7. Requirements & Acceptance Criteria

### Functional Requirements

- [ ] FR-1: Accept `.txt`, `.md`, `.epub`, `.pdf` file uploads (max 50MB)
- [ ] FR-2: Parse and extract clean text from all supported formats
- [ ] FR-3: Chunk text at natural boundaries (chapters, headings) or ≤4000 words
- [ ] FR-4: Detect quoted dialogue using regex patterns (`"..."`, `'...'`, etc.)
- [ ] FR-5: Generate speech using Kokoro-82M with selected voice(s)
- [ ] FR-6: Support playback speed adjustment (0.5x - 2.0x)
- [ ] FR-7: Support output quality selection (SD/HD/Ultra)
- [ ] FR-8: Support MP3 and WAV output formats
- [ ] FR-9: Save audio as individual files per chapter/chunk
- [ ] FR-10: Provide real-time progress with activity log
- [ ] FR-11: Allow canceling in-progress conversions
- [ ] FR-12: Persist library of converted books
- [ ] FR-13: Provide built-in audiobook player
- [ ] FR-14: Support bookmarks and playback position memory
- [ ] FR-15: Voice preview before conversion

### Non-Functional Requirements

- [ ] NFR-1: Support GPU acceleration (CUDA) with CPU fallback
- [ ] NFR-2: Process 4000 words in under 5 minutes on mid-range GPU
- [ ] NFR-3: Web UI must be accessible and usable without developer tools
- [ ] NFR-4: No external API calls — fully offline after model download
- [ ] NFR-5: Dark mode by default with Stitch design system
- [ ] NFR-6: Responsive design for desktop use

## 8. Planning Agent Handoff

> [!IMPORTANT]
> This section is critical for implementation agents.

### Primary Goal for Planner

Build a working end-to-end pipeline: upload a TXT file → generate single chapter MP3 with one voice → play in built-in player.

### Suggested Implementation Order (Phased)

### Phase 1: Core Pipeline (MVP)

1. Backend Core — FastAPI scaffold with file upload endpoint
2. TTS Engine — Kokoro-82M integration, single voice generation
3. File Parser — Start with TXT, add MD/EPUB/PDF incrementally
4. Text Chunker — Implement smart chunking with natural break detection
5. Audio Pipeline — MP3 encoding and chapter file management
6. Progress Tracking — Status endpoint with activity log
7. Upload/Config UI — Basic file upload and voice selection (from Stitch design)
8. Progress UI — Circular progress display (from Stitch design)

### Phase 2: Playback & Library

1. Library Manager — File-based persistence using data/ directory
2. Player UI — Built-in audiobook player (from Stitch design)
3. Library API — CRUD for books and chapters via metadata.json files
4. Dashboard UI — Library grid view (from Stitch design)

### Phase 3: Polish

1. Landing Page UI — Marketing page (from Stitch design)
2. Dialogue Detector — Quote pattern matching for voice switching
3. Voice Preview — Sample playback before conversion
4. Bookmarks — Save and restore playback positions
5. Advanced Settings — Quality, speed, format options

### Risks to Watch

| Risk | Mitigation |
| ---- | ---------- |
| GPU memory limits | Use streaming/batched inference, test with long documents |
| EPUB parsing complexity | Use well-tested ebooklib, handle edge cases gracefully |
| Dialogue detection accuracy | Start simple (regex), allow user override in future |
| Large file processing time | Show granular progress, allow background processing |
| Frontend complexity | Use Stitch HTML as starting point, adapt incrementally |

### Reference Files

- `kokoro` - PyPI package for TTS model
- `ebooklib` - EPUB parsing library
- `PyMuPDF` - PDF text extraction
- `docs/stitch/` - UI design mockups and HTML templates

## 9. Open Questions

- [x] ~~Should we support pausing/resuming long generation jobs?~~ → Yes (Cancel shown in UI)
- [x] ~~What's the maximum file size we should support?~~ → 50MB (per Stitch UI)
- [ ] Should chapter MP3s include ID3 metadata (title, track number, cover art)?
- [x] ~~Do we want a "preview" mode to test voices before full generation?~~ → Yes (Voice cards have play buttons)
- [x] ~~Should we persist job history for re-downloading previous conversions?~~ → Yes (Dashboard shows library)
- [ ] Should we extract/generate book cover art from uploaded files?
- [ ] How should we handle very long books (500+ pages)?

---

*Blueprint created: 2026-02-07*
*Updated: 2026-02-07 (Stitch UI integration)*
*Model: Kokoro-82M*
*Status: Awaiting user approval*
