---
name: code-review
description: "Reviews code changes for correctness, security, and maintainability with actionable feedback. Triggers on: review this code, code review, check this PR, review my changes."
---

# Code Review

## Table of Contents

1. [Inputs needed](#inputs-needed-ask-first-if-missing)
2. [How to conduct a high-quality review](#how-to-conduct-a-high-quality-review)
3. [Workflow](#workflow)
4. [Checklist](#checklist)
5. [Best Practices](#best-practices)
6. [Output Format](#output-format)
7. [Final Note](#final-note)

## Inputs needed (ask first if missing)

- Scope: PR/diff vs. full repo, specific files/folders to focus on.
- Context: expected behavior/requirements, acceptance criteria, and any relevant tickets/spec.
- Constraints: performance/SLA targets, security sensitivity, backward compatibility requirements.
- Tech: language/runtime/framework versions, style guide/lint rules, testing expectations.

## How to conduct a high-quality review

Review with a focus on simplicity, readability, robustness, and elegance. Prefer concrete, minimal changes over broad rewrites.

## Workflow

1. Initial Assessment
   - Quickly identify the code's purpose and overall structure. Look for the forest before examining the trees.
2. Deep Logic & Edge Case Analysis
   - Trace the logic flow for all possible execution paths.
   - Identify potential edge cases (null values, empty strings, boundary conditions).
   - Look for race conditions, deadlocks, or resource leaks in asynchronous or multi-threaded code.
   - Verify that business logic aligns with the intended requirements.
3. Simplification & Minimalism Analysis
   - Identify redundant code, unnecessary abstractions, or over-engineering.
   - Look for opportunities to reduce cyclomatic complexity.
   - Suggest removing code that doesn't add clear value.
   - Recommend combining similar functions or extracting common patterns.
   - Challenge every level of indirection - is it truly needed?
4. Best Practices & Security Review
   - Ensure SOLID principles are followed where appropriate.
   - Check for proper error handling and logging.
   - Verify naming conventions are clear and self-documenting.
   - Assess whether the code follows the principle of least surprise.
   - Look for security vulnerabilities (e.g., unsanitized inputs, hardcoded secrets).
   - Identify potential performance issues that stem from poor design.
5. Elegance & Idiomatic Enhancement Suggestions
   - Suggest more idiomatic approaches for the language being used.
   - Recommend functional approaches where they increase clarity.
   - Identify where declarative code would be cleaner than imperative.
   - Look for opportunities to leverage built-in language features.
   - Suggest ways to make the code more composable and reusable.
6. Documentation & Testability Review
   - Check if the code is easy to test. Suggest refactoring for better testability if needed.
   - Ensure complex logic is adequately commented (explaining _why_, not _what_).
   - Verify that public APIs have clear documentation/type hints.
7. Evidence Standard (avoid false positives)
   - For every concern, cite evidence: file + line(s) when available, or a precise snippet.
   - If you cannot prove an issue from the available code/context, label it as a question or hypothesis and ask for clarification.
8. Generate Feedback
   - Generate the final feedback report. Structure the output according to the provided format, prioritizing critical issues. Save the report as a markdown file.

## Checklist

Use the tools available to create a TODO list to track your progress:

- [ ] Confirm input files and review scope.
- [ ] Perform deep logic and edge case analysis.
- [ ] Identify opportunities for simplification and code removal.
- [ ] Validate best practices, security, and naming conventions.
- [ ] Prepare idiomatic and elegance enhancement suggestions.
- [ ] Review documentation and testability.
- [ ] Compile final review using the structured output format.

## Best Practices

- Simplicity: Strive to make the code as simple as possible. Every line should justify its existence. Remove unnecessary abstractions, redundant logic, and convoluted structures.
- Readability: Prioritize clarity over cleverness. Ensure intent is communicated effectively.
- Minimalism: The best code is often the code you don't write. Ensure that every line serves a clear purpose. Eliminate anything non-essential or not contributing meaningfully to functionality.
- Robustness / Security: The code must be resilient. Identify potential edge cases, race conditions, and security vulnerabilities (e.g., injection, improper validation). Ensure error handling is comprehensive but not over-engineered.
- Elegance: Elegance emerges from clarity of intent and economy of expression. Advocate for code that is not only functional but also beautiful in its clarity and expressiveness. Promote idiomatic patterns and known best practices.
- Pragmatism: Balance the "perfect" solution with practical constraints.
- Context Awareness: Respect project-specific patterns while suggesting improvements within those constraints.
- Expansive Review: For small to medium-sized projects, provide a thorough and detailed review. Don't hesitate to suggest improvements even for minor details if they contribute to long-term maintainability.
- Scope: Focus on recently written or modified code, but also consider how it interacts with the existing codebase. If a change reveals a flaw in the surrounding code, point it out.
- No False Positives: If the code is already excellent, say so - don't invent problems just to have something to say.
- Feedback Style: Be direct but constructive. Provide concrete, minimal-change examples. Acknowledge good patterns.

## Output Format

Structure your review as follows:

### Summary

Brief overview of the code's quality and main concerns (2-3 sentences).

### Critical Issues (Logic, Security, Performance)

Use severity labels: Blocker, Major, Minor, Nit.

- Issue description
- Evidence (file/line or snippet)
- Suggested improvement (minimal diff) + explanation

### Logic & Edge Cases

- Analysis of execution paths and boundary conditions
- Potential bugs or unhandled scenarios

### Simplification & Minimalism

- What can be removed or combined
- Specific refactoring suggestions with examples

### Elegance & Idiomatic Enhancements

- Pattern improvements
- Better use of language features

### Documentation & Testability Recommendations

- Suggestions for better comments or documentation
- Refactoring for improved unit testing

### Positive Observations

- What's already well done (be specific).

## Final Note

Remember: Your goal is to help create code that other developers will thank the author for writing. Every suggestion should move toward that goal.
