# PDF Flow Preservation

This document describes the current PDF upload-to-audiobook flow that should remain stable while TXT and ZIP handling continue to evolve.

TXT and Gutenberg ZIP sources now follow separate parser-backed ingestion paths. This document remains the preservation reference for the dedicated Docling-backed PDF path only.

## Goal

The PDF path is the clean reference flow in SimplyNarrated today. It works well because PDFs are routed directly to the Docling converter without the parser-specific preprocessing used for TXT and ZIP sources.

Future refactors should preserve this behavior unless there is an explicit decision to redesign the PDF path too.

## Control Flow

1. Upload starts in [src/api/routes.py](src/api/routes.py#L177) at `upload_file()`.
2. The API validates the extension and size, then stores the uploaded PDF in `data/uploads/{uuid}.pdf`.
3. Generation starts in [src/api/routes.py](src/api/routes.py#L227) at `start_generation()`.
4. The job manager queues background work in [src/core/job_manager.py](src/core/job_manager.py#L212).
5. The pipeline in [src/core/pipeline.py](src/core/pipeline.py#L47) moves the source PDF into `data/library/{book_id}/source.pdf`.
6. The pipeline calls [src/core/document_router.py](src/core/document_router.py#L18) `convert_source_document()`.
7. The router dispatches PDF input to [src/core/docling_adapter.py](src/core/docling_adapter.py#L64) `convert_pdf_document()`.
8. Docling converts the PDF into its internal document model inside [src/core/docling_adapter.py](src/core/docling_adapter.py#L64).
9. The adapter extracts structured chunks, resolves the title, and groups content into `ImportedChapter` objects.
10. The speech renderer in [src/core/speech_renderer.py](src/core/speech_renderer.py#L31) converts each imported chapter into the exact narration text that will be sent to TTS.
11. The TTS engine in [src/core/tts_engine.py](src/core/tts_engine.py#L182) generates raw audio for each chapter.
12. The encoder in [src/core/encoder.py](src/core/encoder.py#L59) writes MP3 files, and [src/core/encoder.py](src/core/encoder.py#L95) embeds ID3 metadata such as title, author, track number, and cover art.
13. The pipeline saves the speech text as `chapter_NN.txt` and writes `metadata.json` after successful chapter generation.

## Why PDF Works Well

  - PDFs are passed through unchanged before Docling conversion.
  - Chapter text is derived after Docling has already created structure, rather than guessed before conversion.
  - The downstream TTS and encoding path works from stable, saved chapter text.

## Invariants To Preserve

  - PDF input must bypass TXT and ZIP preprocessing.
  - `source.pdf` must be moved into the book directory before finalization.
  - Saved chapter text must match the text sent to TTS.
  - Chapter files must keep the `chapter_{N:02d}` naming convention.
  - `metadata.json` must contain `id`, `title`, `author`, `cover_url`, `total_chapters`, `total_duration`, and `chapters`.
  - PDF imports must not attempt automatic author or cover extraction.

## Out Of Scope

  - TXT parser behavior
  - Markdown preprocessing
  - ZIP/HTML extraction and Gutenberg cleanup
  - Chapter reconvert behavior after text editing

Those paths can be refactored independently as long as the PDF preservation tests continue to pass.
