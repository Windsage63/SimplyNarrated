# Skill Template

Copy this template when creating a new skill.

---

## Folder Structure

```markdown
.github/skills/[skill-name]/
├── SKILL.md
└── references/           # Optional, for large examples
    └── example.md
```

---

## SKILL.md Template

````markdown
---
name: skill-name
description: "[What this skill does]. Triggers on: [trigger1], [trigger2], [trigger3]."
---

# [Skill Title]

[One-sentence description of what this skill does.]

## Table of Contents

1. [The Job](#the-job)
2. [Step 1](#step-1-name)
3. [Step 2](#step-2-name)
4. [Output Format](#output-format)
5. [Stopping Rules](#stopping-rules)
6. [Checklist](#checklist)

---

## The Job

1. [First action]
2. [Second action]
3. [Third action]
4. [Fourth action]
5. [Fifth action]

**Important:** [Key constraint or note]

---

## Step 1: [Name]

[Instructions for step 1]

---

## Step 2: [Name]

[Instructions for step 2]

---

## Output Format

[Describe expected output or provide template]

```markdown
# [Output Title]

## Section 1

[Content]

## Section 2

[Content]
```

---

## Stopping Rules

STOP IMMEDIATELY if you consider:

- [Action outside skill scope]
- [Action belonging to another skill]
- [Action requiring explicit user approval]

This skill's SOLE responsibility is [primary function].

---

## Checklist

Before completing, verify:

- [ ] [Verification step 1]
- [ ] [Verification step 2]
- [ ] [Verification step 3]
- [ ] Saved output to [location]
- [ ] Did NOT [stopping rule violation]

````

---

## Quick Checklist for New Skills

Before publishing:

- [ ] Folder name = `name` field (lowercase, hyphens)
- [ ] Description under 200 chars
- [ ] Description includes trigger keywords
- [ ] SKILL.md under 500 lines
- [ ] TOC added (if over 100 lines)
- [ ] Large examples in `references/`
- [ ] Stopping rules defined
- [ ] Completion checklist included
