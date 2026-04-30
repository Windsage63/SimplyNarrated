# TXT Parser Flow

This document describes the TXT ingestion path after removing TXT from the Docling-backed import flow.

## Goal

TXT files do not have the same structural richness as PDFs. Instead of converting TXT to synthetic Markdown and then asking Docling to infer structure, the application now uses a dedicated TXT parser that produces speech-ready chapter text directly.

## Control Flow

1. Upload starts in [src/api/routes.py](src/api/routes.py#L177) at `upload_file()`.
2. The API accepts `.txt`, `.pdf`, and `.zip` uploads. Markdown uploads are disabled for now.
3. The uploaded TXT file is stored in `data/uploads/{uuid}.txt`.
4. Generation starts in [src/api/routes.py](src/api/routes.py#L227) at `start_generation()`.
5. The job manager queues work and [src/core/pipeline.py](src/core/pipeline.py#L47) moves the source file to `data/library/{book_id}/source.txt`.
6. The pipeline calls [src/core/document_router.py](src/core/document_router.py#L18) `convert_source_document()`.
7. The router dispatches TXT input directly to [src/core/text_parser.py](src/core/text_parser.py#L30) `parse_text_document()` instead of Docling.
8. The TXT parser normalizes text, repairs wrapped prose conservatively, detects title and optional author, finds chapter markers when possible, and falls back to word-budget splitting when explicit chapters are missing.
9. The parser writes `source.cleaned.txt` and `parse-report.json` into the book folder so parser behavior is visible and tunable.
10. The parser returns speech-ready chapter text through `ParsedTextDocument` and `ParsedTextChapter`.
11. The pipeline uses that chapter text directly, skipping [src/core/speech_renderer.py](src/core/speech_renderer.py) for TXT.
12. The downstream path remains unchanged: TTS generates audio, encoder writes MP3 files, chapter text is saved as `chapter_NN.txt`, and `metadata.json` is finalized.

## Parser Artifacts

  - `source.cleaned.txt`: normalized full-document text after cleanup and prose reflow
  - `parse-report.json`: parser diagnostics including title source, chapter count, explicit chapter marker count, fallback split usage, and warnings
  - `chapter_NN.txt`: final speech-ready chapter text that is also used by chapter reconvert later

## Invariants To Preserve

  - TXT must bypass Docling and the synthetic Markdown conversion path.
  - `source.txt` must be moved into the book directory before finalization.
  - `source.cleaned.txt` and `parse-report.json` must be written for TXT jobs.
  - Saved `chapter_NN.txt` must match the parser-produced speech-ready text after optional cleanup flags are applied.
  - Chapter files must keep the `chapter_{N:02d}` naming convention.
  - `metadata.json` must retain the existing library contract so player, export, and reconvert flows remain compatible.

## Out Of Scope

  - PDF ingestion changes
  - ZIP/HTML parser behavior beyond the shared router boundary
  - Reintroducing a dedicated Markdown path
  - UI redesign

Markdown can be revisited later, likely by building on the TXT parser path rather than routing Markdown through Docling first.
