---
name: code-review
description: "Reviews code for correctness, security, and maintainability with severity-ranked actionable feedback, when finalizing code for merge or release. Triggers on: review this code, code review, check this PR, review my changes, audit code."
---

# Code Review

Conduct a high-quality professional review of the provided code or changes. Every finding must carry a severity label so the reader can triage and selectively implement recommendations. Prefer concrete, minimal changes over broad rewrites.

## Severity Classification

Every finding in every section of the report **must** carry exactly one of these labels:

| Label       | Meaning                                                                                         | Action Expected                                                    |
| ----------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Blocker** | Prevents correct operation, causes data loss, or opens a security hole.                         | Must fix before merge.                                             |
| **Major**   | Significant bug, performance issue, or design flaw that will cause problems in production.      | Should fix before merge; defer only with documented justification. |
| **Minor**   | Suboptimal pattern, missing edge-case handling, or readability issue with limited blast radius. | Fix when convenient; safe to defer.                                |
| **Nit**     | Style preference, naming nitpick, or trivial improvement with no functional impact.             | Optional; address during routine cleanup.                          |

When uncertain between two levels, choose the higher severity — it is easier to downgrade than to miss a real issue.

## Workflow

1. **Initial Assessment** — Identify the code's purpose and overall structure. Look for the forest before examining the trees.
2. **Deep Logic & Edge Case Analysis** — Trace logic flow for all execution paths. Look for null/empty/boundary conditions, race conditions, deadlocks, and resource leaks.
3. **Simplification & Minimalism** — Challenge every abstraction and level of indirection. Identify redundant code, over-engineering, and opportunities to reduce cyclomatic complexity.
4. **Security & Best Practices** — Check for OWASP Top 10 vulnerabilities, unsanitized inputs, hardcoded secrets, improper auth checks. Verify error handling and naming conventions.
5. **Elegance & Idiomatic Enhancements** — Suggest more idiomatic approaches, functional patterns where they increase clarity, and better use of built-in language features.
6. **Documentation & Testability** — Evaluate testability and suggest refactoring if needed. Check that complex logic explains _why_, not _what_. Verify public API docs/type hints.
7. **Evidence Standard** — For every finding, cite evidence: file + line(s) or a precise snippet. If you cannot prove an issue, label it as a hypothesis and ask for clarification.
8. **Generate Report** — Produce the final report using the Output Format below. Assign a severity label to every individual finding. Build the Prioritized Findings Summary table. Save as a markdown file.

## Checklist

Track progress with a TODO list:

- [ ] Confirm input files and review scope
- [ ] Deep logic and edge case analysis
- [ ] Simplification and code removal opportunities
- [ ] Security audit and best practices validation
- [ ] Idiomatic and elegance enhancements
- [ ] Documentation and testability review
- [ ] Every finding has a severity label assigned
- [ ] Prioritized Findings Summary table is complete
- [ ] Report saved as markdown

## Gotchas

- Do not invent problems to fill sections. If the code is excellent, say so and leave the section empty.
- Severity labels must appear on **individual findings**, not section headers. A single section often contains findings at multiple severity levels.
- "Nit" is not "unimportant" — it signals low urgency, not low quality of the observation.
- When reviewing async Python, check for blocking calls inside `async def` (common miss that doesn't show up in tests).

## Review Guidance

- **Scope:** Focus on recently written or modified code, but flag flaws in surrounding code that a change reveals.
- **Context Awareness:** Respect project-specific patterns (check `copilot-instructions.md`) while suggesting improvements within those constraints.
- **Expansive Review:** For small to medium-sized projects, review thoroughly — minor improvements compound over time.
- **Feedback Style:** Be direct but constructive. Provide concrete, minimal-change examples. Acknowledge good patterns.
- **No False Positives:** If you cannot prove an issue from available code/context, label it as a question or hypothesis. Never fabricate issues.

## Stopping Rules

STOP IMMEDIATELY if you consider:

- Rewriting large sections of code beyond the review scope
- Making opinionated architectural changes without user request
- Reviewing auto-generated files, vendored dependencies, or build artifacts
- Performing fixes directly (this skill produces a report, not code changes)

This skill's SOLE responsibility is producing a structured, severity-ranked review report.

## Output Format

Structure your review as follows. **Every individual finding must include its severity label in bold at the start.**

### Summary

Brief overview of the code's quality and main concerns (2–3 sentences). State the total finding count by severity.

### Critical Issues (Security, Correctness, Performance)

- **[Blocker/Major]** Issue description
  - Evidence (file/line or snippet)
  - Suggested improvement (minimal diff) + explanation

### Logic & Edge Cases

- **[Major/Minor]** Issue description
  - Evidence and suggested improvement

### Simplification & Minimalism

- **[Minor/Nit]** What can be removed or combined
  - Specific refactoring suggestion with example

### Elegance & Idiomatic Enhancements

- **[Minor/Nit]** Pattern improvement
  - Better use of language features with example

### Documentation & Testability

- **[Major/Minor/Nit]** Issue description
  - Suggested improvement

### Positive Observations

- What's already well done (be specific, no severity label needed here).

### Prioritized Findings Summary

Close the report with a scannable triage table. Sort by severity (Blockers first), then by section. This table is the primary tool for selecting items for partial implementation.

| #   | Severity    | Section            | Finding             | Effort         |
| --- | ----------- | ------------------ | ------------------- | -------------- |
| 1   | **Blocker** | Critical Issues    | [Short description] | [Low/Med/High] |
| 2   | **Major**   | Critical Issues    | [Short description] | [Low/Med/High] |
| 3   | **Major**   | Logic & Edge Cases | [Short description] | [Med]          |
| 4   | **Minor**   | Simplification     | [Short description] | [Low]          |
| …   | …           | …                  | …                   | …              |

The **Effort** column estimates implementation complexity: **Low** (< 30 min, localized change), **Med** (hours, touches multiple files), **High** (significant refactor or design change).
