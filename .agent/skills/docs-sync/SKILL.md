---
name: docs-sync
description: "Syncs documentation with code changes by detecting mismatches and producing update reports. Triggers on: update docs, sync documentation, docs out of date, check docs."
---

# Docs Sync

## How to keep the documentation up to date

Follow the workflow below to review the project documentation, sources, diffs, and context to surface mismatches between the code and the documentation. Implement documentation fixes to reconcile the mismatches so the docs align with the source of truth.

## Workflow

1. Begin by confirming the input parameters: the list of documentation files to review, or review all documentation.
2. Identify relevant code areas by analyzing recent changes (diffs), project structure, and key entry points. Avoid scanning the entire codebase if the scope can be narrowed.
3. Cross-reference the identified code elements with the existing documentation to find discrepancies, missing information, outdated references, or incomplete sections.
4. Use any available diffs or commit history to help identify changes which may impact the documentation.
5. Scan the repository (code + existing docs) to detect inconsistencies, TODOs, or undocumented APIs using search tools (e.g., searching for exported symbols, API decorators, or configuration files).
6. For each identified discrepancy, determine if it is:
   - Actionable: Clear mismatch that can be directly addressed with a documentation update.
   - Clarifying: Ambiguous. Requires further context or decisions before a fix can be applied (e.g., code deviates from PRD intent).
7. Create a `Documentation Plan` listing the specific files to be updated and the nature of the changes.
8. For actionable items, implement the documentation updates.
9. For clarifying items, log them within the relevant documents or a central `DOCS_TODO.md` with context for future resolution.
10. Do not invent fixes or assume behavior you cannot prove through code. If the code is the source of truth for implementation, update the docs; if the doc is the source of truth for intent (e.g., PRD), flag the code as deviating.
11. Ensure all documentation updates adhere to the project's style guide, formatting conventions, and linking practices.
12. Validate that all relative links, internal anchors, and code snippets in the updated documentation function correctly.
13. If shared tables or reference sections exist across multiple documents (e.g., API quick reference tables), ensure consistency is maintained across all affected documents.
14. Produce a `Mismatch Report` using the following table format:

    | File | Location | Discrepancy | Type (Actionable/Clarifying) | Proposed Action |
    | :--- | :--- | :--- | :--- | :--- |

15. Compile a final summary report detailing:
    - The number of discrepancies found.
    - The number of actionable items addressed.
    - The number of clarifying items logged with their status.
    - Any recommendations for future documentation improvements or follow-up actions.
16. Conclude with a brief, dry, grumpy one-liner reflecting on the state of the documentation before and after the updates.

## Checklist

Use the tools available to create a TODO list to track your progress similar to below:

- [ ] Confirm inputs: recent diffs, target modules, existing documentation scope.
- [ ] Run repository scans for undocumented modules/endpoints or stale references.
- [ ] Produce a mismatch report with actionable vs. clarifying items separated, presented in the required table format.
- [ ] Ensure updates follow documentation style and linking conventions.
- [ ] Validate navigation, anchors, and code snippets after edits.
- [ ] Confirm shared tables (e.g., API quick references) stay synchronized across documents.
- [ ] Log remaining open questions or future doc enhancements.

## Best Practices

- Targeted Discovery: Prioritize files identified in recent diffs or those containing core logic (e.g., `api.js`, `models/`).
- Intent vs. Implementation: Distinguish between "how it works" (code is truth) and "how it should work" (PRD/Design is truth). Flag deviations rather than blindly updating intent docs to match buggy code.
- Link Integrity: Always verify relative paths (e.g., `[link](../../README.md)`) and internal anchors (e.g., `#setup`) after moving or renaming sections.
- Incremental Updates: For large documentation sets, process and apply changes file-by-file to maintain context and avoid token limits.
- Consistency: Use concise language and consistent terminology aligned with existing docs.
- Transparency: Capture open questions and highlight them in the final report summary.
- Sign-off: End each run with a dry, grumpy one-liner about the documentation state so the team remembers to keep docs salient and current.
