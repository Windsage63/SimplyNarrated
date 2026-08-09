# Skill Template

Copy this template when creating or checking a skill.

## Folder Structure

Follow the canonical file organization structure defined in the parent SKILL.md.

## SKILL.md Template (Minimal)

````markdown
---
name: skill-name
description: "[What the skill does], when [specific contexts, including non-obvious ones]. Triggers on: [trigger1], [trigger2], [trigger3]."
---

# [Skill Title]

[One or two sentence description of what this skill does.]

## The Job

1. [First action]
2. [Second action]
3. [Third action]
4. [Fourth action]
5. [Fifth action]

## [Main Content Section]

[Instructions, patterns, and key information]

## Gotchas

- [Non-obvious fact that defies reasonable assumptions]
- [Edge case the agent would miss without being told]

## Stopping Rules

STOP IMMEDIATELY if you consider:

- [Action outside skill scope]
- [Action belonging to another skill]
- [Action requiring explicit user approval]
- Running shell commands or changing external systems without following the host's approval flow

This skill's SOLE responsibility is [primary function].

## Checklist

Before completing, verify:

- [ ] [Verification step 1]
- [ ] [Verification step 2]
- [ ] [Verification step 3]
- [ ] Saved output to [location]
- [ ] Did NOT [stopping rule violation]

````

## SKILL.md Template (Full)

````markdown
---
name: skill-name
description: "[What the skill does], when [specific contexts]. Triggers on: [trigger1], [trigger2]."
---

# [Skill Title]

[One or two sentence description.]

## The Job

1. [First action]
2. [Second action]
3. [Third action]
4. [Fourth action]
5. [Fifth action]

**Important:** [Key constraint or note]

## Step 1: [Name]

[Instructions for step 1]

## Step 2: [Name]

[Instructions for step 2]

## Output Format

[Describe expected output or provide template]

```markdown
# [Output Title]

## Section 1

[Content]

## Section 2

[Content]
```

## Additional Resources

- For complete API details, see [references/reference.md](references/reference.md)
- For usage examples, see [references/examples.md](references/examples.md)
- For form-specific workflows, read [references/forms.md](references/forms.md) when filling forms

## Gotchas

- [Non-obvious fact 1]
- [Non-obvious fact 2]

## Stopping Rules

STOP IMMEDIATELY if you consider:

- [Action outside skill scope]
- [Action belonging to another skill]
- [Action requiring explicit user approval]
- Running shell commands or changing external systems without following the host's approval flow

This skill's SOLE responsibility is [primary function].

## Checklist

Before completing, verify:

- [ ] [Verification step 1]
- [ ] [Verification step 2]
- [ ] [Verification step 3]
- [ ] Saved output to [location]
- [ ] Did NOT [stopping rule violation]

````

## Quick Checklist for New Skills

Run the verification checklist from the parent SKILL.md before finalizing. Additionally, verify:

  - [ ] Tested with representative queries
