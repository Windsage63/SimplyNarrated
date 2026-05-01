# SimplyNarrated Testing Guide

> **Last updated:** 2026-04-30

This document describes how tests are run in this repository, what each test slice covers, and which recent behavior changes are now protected by regression tests.

## Test Runner

Use the embedded interpreter shipped with the repository:

```powershell
.\python_embedded\python.exe -m pytest
```

In this workspace, pytest should also be given explicit cache and temp locations:

```powershell
.\python_embedded\python.exe -m pytest -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp
```

## Common Commands

Run the default non-live suite:

```powershell
.\python_embedded\python.exe -m pytest -m "not live_tts" -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp
```

Run the live TTS tests only:

```powershell
.\python_embedded\python.exe -m pytest -m live_tts -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp
```

Run recently updated regression slices:

```powershell
.\python_embedded\python.exe -m pytest tests/test_frontend_smoke.py tests/test_gutenberg_parser.py tests/test_upload_policy.py tests/test_chapter_reconvert_api.py tests/test_pipeline_pdf.py -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp
```

## Pytest Configuration

  - Test root: `tests/`
  - Config file: `pytest.ini`
  - Custom marker: `live_tts`
  - Live tests exercise the real TTS runtime and generate audio artifacts.

## Test Coverage Map

The repository does not currently check in a numeric coverage threshold or a mandatory coverage report. Coverage is tracked here by behavior and test slice.

| Test file | Primary coverage |
| --- | --- |
| `tests/test_frontend_smoke.py` | Served frontend assets, exposed player hooks, upload UI contract, safe text rendering regressions, progress teardown wiring |
| `tests/test_upload_policy.py` | Upload extension policy for source files and route-level cover upload validation |
| `tests/test_gutenberg_parser.py` | Gutenberg ZIP parsing, cleanup rules, unsafe members, fallback chapter splitting, archive member limits, oversized HTML rejection, oversized cover rejection |
| `tests/test_text_parser.py` | Plain-text parsing and chapter extraction behavior |
| `tests/test_txt_path.py` | TXT import path behavior and file-path handling |
| `tests/test_docling_adapter_pdf.py` | PDF conversion integration boundary and docling adapter expectations |
| `tests/test_document_router.py` | Source routing between TXT, PDF, and ZIP import paths |
| `tests/test_pipeline_pdf.py` | Main PDF-to-audiobook pipeline contract, metadata writing, cancellation-after-blocking-step behavior |
| `tests/test_pipeline_pdf_live_tts.py` | PDF pipeline with the real TTS runtime |
| `tests/test_chapter_reconvert_api.py` | Chapter text save API, reconvert queueing, duplicate reconvert reuse, reconvert offloading, reconvert cancellation-after-blocking-step behavior |
| `tests/test_chapter_reconvert_live.py` | Single-chapter reconvert path with live TTS |
| `tests/test_encoder.py` | Audio encoding and MP3 metadata embedding |
| `tests/test_speech_renderer.py` | Final speech text rendering and cleanup behavior |
| `tests/test_metadata_store.py` | Metadata file atomic update behavior |
| `tests/test_job_manager_retention.py` | Job ledger retention and pruning logic |
| `tests/test_tts_live.py` | Core live TTS engine audio generation |
| `tests/test_txt_live.py` | TXT ingestion plus live TTS generation path |

## Coverage Added For The 2026-04-30 Fixes

  - Frontend regressions now check that the served dashboard, player, and progress scripts render dynamic text through safe assignments instead of vulnerable inline HTML patterns.
  - Progress-view lifecycle coverage now checks that teardown hooks exist both in the progress view script and in the app-level view switch logic.
  - Gutenberg ZIP parser coverage now includes member-count limits, total uncompressed-size limits, per-HTML size limits, and oversized ZIP cover rejection.
  - Cover upload coverage now checks that spoofed image uploads are rejected and that saved cover type follows detected file bytes rather than client MIME alone.
  - Chapter reconvert coverage now checks that duplicate same-chapter requests reuse an active job instead of queueing a second job.
  - Pipeline and reconvert coverage now check that cancellation stops later write/finalize work after a blocking TTS step returns.

## Live Test Notes

  - `live_tts` tests require the local runtime assets and a working TTS environment.
  - Live tests are slower and generate real audio artifacts during execution.
  - Use `-m "not live_tts"` for normal local iteration unless you are explicitly validating the real runtime path.

## Known Gaps

  - There is still no browser-automation suite that executes the frontend in a real DOM; frontend coverage is currently source- and route-level.
  - There is still no checked-in numeric coverage report or CI coverage gate.
  - Cover validation currently relies on byte-signature detection for JPEG and PNG, not full image decode and normalization.

## Recent Validation Commands

These commands were used to validate the latest fixes:

```powershell
.\python_embedded\python.exe -m pytest tests/test_frontend_smoke.py -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp
.\python_embedded\python.exe -m pytest tests/test_gutenberg_parser.py -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp
.\python_embedded\python.exe -m pytest tests/test_upload_policy.py -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp
.\python_embedded\python.exe -m pytest tests/test_chapter_reconvert_api.py tests/test_pipeline_pdf.py -o cache_dir=C:\tmp\simplynarrated_pytest_cache --basetemp=C:\tmp\simplynarrated_pytest_temp
```
