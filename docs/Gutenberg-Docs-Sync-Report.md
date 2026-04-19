# Docs-Sync Report — Gutenberg Paragraph Reflow

> **Scope:** All documentation files affected by the Gutenberg HTML normalization changes in `src/core/docling_adapter.py`.

## Mismatch Report

| File | Location | Discrepancy | Type | Action Taken |
| --- | --- | --- | --- | --- |
| [example-outputs.md](example-outputs.md) | `# Output Eamples` (L1) | Heading typo: "Eamples" instead of "Examples" | Actionable | Fixed to "Output Examples" |
| [example-outputs.md](example-outputs.md) | `## Output from a Project Guttenberg` (L3) | Typo: "Guttenberg" (double-t) instead of "Gutenberg" | Actionable | Fixed to "Gutenberg" |
| [example-outputs.md](example-outputs.md) | `## Example Input from Project Guttenberg` (L46) | Typo: "Guttenberg" (double-t) instead of "Gutenberg" | Actionable | Fixed to "Gutenberg" |
| [AGENTS.md](../AGENTS.md) | Architecture section (L58) | Architecture summary did not mention Gutenberg HTML preprocessing step | Actionable | Added "Gutenberg ZIP HTML is preprocessed (boilerplate removal and paragraph reflow) before Docling conversion" |
| [AGENTS.md](../AGENTS.md) | `docling_adapter.py` description (L67) | Module description omitted Gutenberg normalization role | Actionable | Updated to "…cover extraction, and Gutenberg HTML normalization" |
| [API-Reference.md](API-Reference.md) | Upload endpoint ZIP behavior (L30-37) | No mention of paragraph reflow preprocessing step | Actionable | Added bullet: "Reflows soft-wrapped prose paragraphs in the source HTML before Docling conversion" |
| [README.md](../README.md) | Features → Gutenberg Import (L19) | Paragraph reflow behavior not mentioned | Actionable | Appended: "Soft-wrapped prose paragraphs are reflowed before conversion so TTS output sounds natural" |

## Summary

  - **Discrepancies found:** 7
  - **Actionable items addressed:** 7
  - **Clarifying items logged:** 0
  - **Recommendations:**
    - The follow-up plan doc itself (`Docling-Gutenberg-Followup-Plan.md`) should eventually be archived or removed once all follow-up work is complete, to avoid confusion about what is still pending vs. done.
    - Consider adding a brief note to the `example-outputs.md` file showing the *after* output (reflowed prose) alongside the existing *before* example, so future contributors can see the improvement.

> The documentation was optimistic enough to describe the feature but not thorough enough to mention how it actually works. Classic.
