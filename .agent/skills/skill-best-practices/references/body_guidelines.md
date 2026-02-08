# Body Content Guidelines

Best practices for structuring SKILL.md body content.

---

## Length Constraints

| Metric | Limit | Notes |
| ------ | ----- | ----- |
| Total lines | 500 | Hard limit for performance |
| Total words | 5,000 | Approximate token budget |
| TOC required | 100+ lines | Helps Claude navigate |

---

## Conciseness Principles

### 1. Assume Claude is Smart

Claude already knows:

- Common programming patterns
- Language syntax and idioms
- General software engineering principles
- Standard security practices

**Only add:**

- Project-specific context
- Non-obvious workflows
- Custom output formats
- Explicit constraints

### 2. Question Every Line

Before including content, ask:

- Does Claude need this to complete the task?
- Is this information available elsewhere in the codebase?
- Can this be expressed more concisely?
- Does this justify its token cost?

### 3. Examples Over Explanations

```markdown
# Bad: Verbose explanation
The output should be formatted as a markdown table with three columns.
The first column should contain the component name. The second column
should contain a brief description. The third column should indicate
the priority level using P0, P1, or P2.

# Good: Concise example
| Component | Description | Priority |
|-----------|-------------|----------|
| Auth | User authentication | P0 |
```

### 4. No Duplication

Information should exist in exactly one place:

- Core instructions → SKILL.md
- Large examples → `references/`
- External schemas → link to source

---

## Recommended Structure

### Core Sections (Required)

```markdown
## The Job
Brief numbered workflow (5-7 steps max)

## [Main Content]
Skill-specific instructions and patterns

## Stopping Rules
Explicit "do NOT" constraints

## Checklist
Verification steps before completion
```

### Optional Sections

```markdown
## Table of Contents
Required for files over 100 lines

## Quick Reference
Summary table for key constraints

## Examples
Brief inline examples (extract large ones)

## Output Format
Template for skill output
```

---

## Table of Contents Pattern

For files over 100 lines, add TOC after the opening description:

```markdown
## Table of Contents

1. [The Job](#the-job)
2. [Step 1: Name](#step-1-name)
3. [Step 2: Name](#step-2-name)
4. [Output Format](#output-format)
5. [Stopping Rules](#stopping-rules)
6. [Checklist](#checklist)
```

**Anchor format:** `#section-name` (lowercase, hyphens for spaces)

---

## Stopping Rules Pattern

Always include explicit constraints:

```markdown
## Stopping Rules

STOP IMMEDIATELY if you consider:

- [Action that violates scope]
- [Action that belongs to another skill]
- [Action that requires user approval]

This skill's SOLE responsibility is [primary function].
```

---

## Checklist Pattern

End with verification steps:

```markdown
## Checklist

Before completing, verify:

- [ ] [Verification step 1]
- [ ] [Verification step 2]
- [ ] [Output saved to correct location]
- [ ] [Did NOT violate stopping rules]
```

---

## What to Avoid

| Anti-Pattern | Why It's Bad |
| ------------ | ------------ |
| Explaining basic concepts | Wastes tokens on what Claude knows |
| Repeating information | Inflates file size, risks inconsistency |
| Vague instructions | "Make it good" vs "Follow this template" |
| Nested conditionals | Hard to follow, error-prone |
| Wall of text | No structure, hard to navigate |
