# Docling Gutenberg Follow-Up Plan

> Created: 2026-04-17  
> Audience: Follow-up agent doing cleanup, instruction updates, and documentation sync

## Purpose

This document captures the work completed to fix Project Gutenberg HTML soft-wrapped paragraph line endings, the reasoning behind the implementation choice, the current verification status, and the remaining follow-up work.

The immediate bug is fixed. This handoff is for tightening the code, syncing project instructions, and updating user-facing documentation so the repo reflects the current Docling-based import pipeline accurately.

## What Was Implemented

### Problem

Project Gutenberg ZIP uploads contain HTML where prose inside `<p>` tags is often source-wrapped across many lines. Those line breaks were surviving into Docling chunk text and then into generated chapter text, causing TTS to pause at the end of each source line.

PDF imports were already producing well-flowed text, so the issue was specific to Gutenberg HTML source formatting.

### Decision

The fix was implemented before Docling conversion, not in the downstream narration text normalizer.

Why:

  - The app already opens Gutenberg ZIP files and extracts the HTML itself before handing it to Docling.
  - A Gutenberg-specific HTML cleanup pass is narrower and safer than a generic narration-layer flattening pass.
  - This preserves the Docling import pipeline while giving Docling cleaner HTML to parse.
  - Chapter reconvert behavior remains unchanged because reconvert reads the saved `chapter_NN.txt` directly.

### Code Changes

The main change is in `src/core/docling_adapter.py`.

Implemented behavior:

  - ZIP imports still extract the largest HTML file from the archive.
  - The extracted HTML now flows through `_normalize_gutenberg_html()` before being written to the temporary `gutenberg.html` file.
  - Paragraph reflow is limited to `<p>...</p>` blocks.
  - Only paragraphs that look like wrapped prose are flattened.
  - Verse-like or short intentionally line-broken paragraphs are left intact.

The current reflow heuristic uses:

  - minimum line count
  - minimum average line length
  - minimum max line length
  - a prose-continuation check across adjacent lines
  - rejection of paragraphs with internal blank lines

### Test Coverage Added

Added regression coverage in `tests/test_docling_adapter.py` for:

  - wrapped Gutenberg prose paragraph reflow
  - preserving short verse-like paragraphs
  - end-to-end ZIP import proving cleaned paragraph text reaches Docling output

## Files Involved

### Primary implementation file

  - `src/core/docling_adapter.py`

Key functions added or changed:

  - `_extract_html_from_zip_to_temp()`
  - `_normalize_gutenberg_html()`
  - `_normalize_gutenberg_paragraph_wrapping()`
  - `_looks_like_wrapped_gutenberg_prose()`
  - `_looks_like_prose_continuation()`

### Primary tests

  - `tests/test_docling_adapter.py`

### Supporting reference material

  - `docs/example-outputs.md` or `docs/Example-outputs.md`, depending on final normalized path chosen in follow-up cleanup

## Verification Status

### Manual result

The user confirmed that a real Gutenberg conversion worked very well after the change, including chapter quality and parsing quality overall.

### Automated verification completed

Targeted test:

```bash
python_embedded\python.exe -m pytest tests/test_docling_adapter.py
```

Result:

  - 7 tests passed

Broader non-slow suite:

```bash
python_embedded\python.exe -m pytest tests/ -m "not slow"
```

Result:

  - 157 collected
  - 13 deselected
  - 144 passed

Warnings observed during broader run:

  - `pydub` deprecation warning for `audioop`
  - `pydub` runtime warning about `ffmpeg/avconv` not found
  - 2 Docling deprecation warnings on the PDF path

These warnings were pre-existing and were not introduced by the Gutenberg reflow change.

## Remaining Follow-Up Work

## 1. Code Cleanup

The implementation is working, but there is room to clean up the current heuristic and supporting structure.

Recommended review items:

  - Re-evaluate whether regex-only paragraph targeting is sufficient long-term or whether a light HTML parser pass would make the logic clearer.
  - Review the heuristic constants in `src/core/docling_adapter.py` and decide whether they should remain inline constants, become documented tuning knobs, or move into a dedicated helper section.
  - Decide whether the Gutenberg normalization functions should stay in `docling_adapter.py` or move into a smaller helper module if the adapter grows further.
  - Review whether standalone HTML imports should eventually share the same cleanup path as ZIP-extracted Gutenberg HTML, or whether the behavior should remain ZIP-specific.

## 2. Edge-Case Hardening

The current heuristic is intentionally conservative, but it should be hardened with more representative samples.

Recommended additions:

  - Add one or two real poetry-like Gutenberg paragraph fixtures.
  - Add a prose paragraph case that wraps after commas and sentence endings.
  - Add a mixed-content case where a chapter contains both normal prose and intentionally line-broken content.
  - Confirm that dialogue-heavy wrapped paragraphs continue to reflow correctly.

## 3. Instruction File Updates

A follow-up agent should review the instruction files to ensure they reflect the current state of the codebase and this Gutenberg cleanup behavior where useful.

Recommended files to review:

  - `AGENTS.md`
  - `.github/instructions/testing.instructions.md`
  - `.github/instructions/markdown.instructions.md`

Specific instruction sync opportunities:

  - Make sure the architecture section clearly reflects that Docling is the import-time parser/chunking boundary.
  - Mention that Gutenberg ZIP HTML is preprocessed before Docling conversion for source cleanup.
  - Ensure testing guidance points contributors toward `tests/test_docling_adapter.py` for import-path regressions.

## 4. Documentation Updates

The code behavior is ahead of the docs. A follow-up agent should sync that.

Recommended files to review:

  - `README.md`
  - `docs/API-Reference.md`
  - `docs/example-outputs.md` or `docs/Example-outputs.md`

Recommended documentation updates:

  - Document that Gutenberg ZIP imports now reflow wrapped prose paragraphs before Docling conversion.
  - Clarify that this is a source HTML normalization step, not a generic TTS text rewrite.
  - Update import-pipeline descriptions to match the current Docling adapter and speech renderer flow.
  - If appropriate, add a short note that reconvert still uses saved chapter text directly and is unaffected by this import-side fix.

## 5. Documentation/File Hygiene

There appears to be cleanup debt around documentation naming and consistency that should be resolved carefully.

Items to inspect:

  - The example outputs document may currently exist with inconsistent casing or path representation.
  - The heading `Output Eamples` in the example file should be corrected.
  - Confirm there is only one canonical example outputs file in `docs/` after cleanup.

## Suggested Follow-Up Sequence

1. Read `src/core/docling_adapter.py` and `tests/test_docling_adapter.py` to understand the current heuristic.
2. Inspect the docs tree and normalize the example outputs file naming and content.
3. Update `AGENTS.md` and any relevant `.instructions.md` files so they match the Docling-based import flow and current regression coverage.
4. Sync `README.md` and any other user-facing docs with the Gutenberg reflow behavior.
5. Add a few more representative Gutenberg edge-case tests if the heuristic is being adjusted.
6. Re-run the non-slow test suite.

## Constraints For Follow-Up Changes

  - Do not move the Gutenberg fix into chapter reconvert.
  - Do not add a generic downstream narration-layer flattening pass unless there is a demonstrated residual issue after the source cleanup.
  - Preserve the current rule that saved `chapter_NN.txt` is the canonical reconvert input.
  - Avoid broad HTML rewriting outside paragraph-level Gutenberg cleanup unless there is a specific failing case.

## Short Summary For The Next Agent

The Gutenberg line-break bug is fixed by preprocessing extracted Gutenberg HTML paragraphs before Docling conversion. The current implementation is working well in both real use and automated tests. Your job is not to re-solve the bug from scratch. Your job is to clean up the implementation, harden edge-case coverage, and synchronize the instructions and documentation with the current Docling-based architecture.
