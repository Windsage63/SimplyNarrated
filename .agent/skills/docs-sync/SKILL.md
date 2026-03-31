---
name: docs-sync
description: "Syncs documentation with code changes by detecting mismatches and producing actionable update reports, when docs may be stale after code changes or before a release. Triggers on: update docs, sync documentation, docs out of date, check docs, docs don't match, API docs wrong, stale docs."
---

# Docs Sync

Surface mismatches between code and documentation. Implement fixes for clear discrepancies; flag ambiguous deviations for human review.

## The Job

1. Confirm inputs — target docs, recent diffs, scope
2. Discover mismatches — cross-reference code against documentation
3. Classify each discrepancy as **Actionable** or **Clarifying**
4. Create a Documentation Plan listing files and changes
5. Implement actionable fixes; log clarifying items to `DOCS_TODO.md`
6. Validate links, anchors, and shared tables across all affected documents
7. Produce the Mismatch Report and summary

## Workflow

### Scoping

- Confirm the documentation files to review, or default to all docs.
- Narrow scope using recent diffs, project structure, and key entry points. Avoid scanning the entire codebase when scope can be inferred.

### Discovery

- Cross-reference code elements with existing documentation to find discrepancies, missing information, outdated references, or incomplete sections.
- Use diffs or commit history to identify changes that may impact documentation.
- Scan for inconsistencies, TODOs, or undocumented APIs using search tools (exported symbols, API decorators, configuration files).

### Classification

For each discrepancy, classify it:

- **Actionable** — Clear mismatch that can be directly addressed with a documentation update.
- **Clarifying** — Ambiguous; requires further context or decisions before a fix can be applied (e.g., code deviates from PRD intent).

### Execution

- Create a Documentation Plan listing specific files and the nature of changes.
- For actionable items, implement the documentation updates.
- For clarifying items, log them in the relevant document or a central `DOCS_TODO.md` with context for future resolution.
- If shared tables or reference sections exist across multiple documents (e.g., API quick reference tables), propagate changes to all affected documents.

### Validation

- Verify all relative links, internal anchors, and code snippets function correctly after edits.
- Confirm documentation updates follow the project's existing style, formatting, and linking conventions.

### Reporting

Produce the Mismatch Report and summary using the output format below.

## Output Format

### Mismatch Report

| File                  | Location    | Discrepancy                   | Type       | Proposed Action   |
| :-------------------- | :---------- | :---------------------------- | :--------- | :---------------- |
| docs/API-Reference.md | `## Upload` | Missing `max_file_size` param | Actionable | Add parameter row |

### Summary

- **Discrepancies found:** N
- **Actionable items addressed:** N
- **Clarifying items logged:** N (see `DOCS_TODO.md`)
- **Recommendations:** [brief list]

> [Dry, grumpy one-liner reflecting on the state of the documentation - a la Bertram Gilfoyle]

## Gotchas

- **Intent vs. implementation:** PRDs and design docs describe _desired_ behavior. If code deviates from a PRD, flag the code as deviating — do not silently update the PRD to match buggy code.
- **Shared tables drift independently.** A fix to an API quick-reference table in one doc must propagate to every doc that contains a copy of that table.
- **Generated metadata is not user-editable.** Fields like `duration` or `chapter_count` in `metadata.json` are computed at conversion time. Do not document them as configurable.
- **Route docstrings and API reference can diverge.** Always check both the inline code docstrings and the standalone API docs — they drift independently.

## Stopping Rules

STOP IMMEDIATELY if you consider:

- Updating PRD/design docs to match code that may be buggy (intent docs are source of truth for _intent_)
- Inventing behavior you cannot prove exists in the code
- Modifying source code to match documentation
- Rewriting documentation style or tone beyond what's needed to fix mismatches

This skill's SOLE responsibility is aligning documentation with the current state of the codebase.

## Checklist

Track progress using the available TODO list tools:

- [ ] Confirm inputs: recent diffs, target modules, documentation scope
- [ ] Run repository scans for undocumented modules/endpoints or stale references
- [ ] Produce mismatch report with actionable vs. clarifying items in the required table format
- [ ] Validate links, anchors, and code snippets after edits
- [ ] Confirm shared tables stay synchronized across all affected documents
- [ ] Log remaining open questions or future doc enhancements

## Best Practices

- **Targeted discovery:** Prioritize files from recent diffs or those containing core logic (e.g., `routes.py`, `models/`).
- **Incremental updates:** For large documentation sets, process file-by-file to maintain context and avoid token limits.
- **Transparency:** Capture open questions and surface them in the final report summary.
