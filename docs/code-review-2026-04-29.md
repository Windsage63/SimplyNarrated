# SimplyNarrated Code Review

Review date: 2026-04-29

## Summary

The recent import-pipeline changes are directionally good: the routing split is cleaner, the focused tests pass, and the portability code is substantially more defensive than the older library/job paths. The earlier blocker around blocking file/media I/O in the async job paths has been addressed, and the previously remaining follow-up items from this review have now been resolved in the current branch.

Findings by severity: 0 Blocker, 0 Major, 0 Minor, 0 Nit.

## Critical Issues

No blocker-level issues remain in the reviewed scope after removing PDF enrichment and offloading blocking file and media operations from the async pipeline and route handlers.

## Review Status

No active findings remain in the reviewed scope.

The previously open items were resolved by:
- adding atomic, path-scoped metadata updates in [src/core/metadata_store.py](src/core/metadata_store.py) and wiring [src/core/chapter_reconvert.py](src/core/chapter_reconvert.py) plus [src/core/library.py](src/core/library.py) through that shared helper
- adding async regression coverage for the pipeline, chapter reconvert path, and metadata update route in [tests/test_txt_path.py](tests/test_txt_path.py) and [tests/test_chapter_reconvert_api.py](tests/test_chapter_reconvert_api.py)
- deduplicating source-format detection through [src/core/source_format.py](src/core/source_format.py)
- extending Gutenberg ZIP coverage for malformed archives, unsafe members, and no-marker fallback splitting in [tests/test_gutenberg_parser.py](tests/test_gutenberg_parser.py)

## Deployment Scope Note

SimplyNarrated is currently designed as a local-only desktop application: embedded Python, local model assets, one-click `install.bat`, and novice-user `run.bat` startup. Findings that matter only for a network-exposed multi-user deployment are therefore out of scope for current triage and should only be reopened if remote hosting becomes a product goal.

## Positive Observations

- The new routing split in [src/core/document_router.py](src/core/document_router.py) keeps [src/core/pipeline.py](src/core/pipeline.py) linear and easier to reason about.
- The portability import/export flow in [src/core/portability.py](src/core/portability.py) is comparatively defensive: it normalizes archive members, enforces limits, and stages imports before moving them into place.
- The focused tests for the new import surfaces passed locally: `tests/test_document_router.py`, `tests/test_gutenberg_parser.py`, and `tests/test_docling_adapter_pdf.py` all passed in one run.
- The focused tests for the async I/O fix and its regression guards also passed locally: `tests/test_pipeline_pdf.py`, `tests/test_txt_path.py`, `tests/test_chapter_reconvert_api.py`, and `tests/test_metadata_store.py`.
- The Gutenberg parser has a sensible, readable cleanup pipeline and writes diagnostics that make parser tuning observable instead of opaque.

## Prioritized Findings Summary

No active findings.