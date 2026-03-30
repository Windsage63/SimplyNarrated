# Skill Template

Copy this template when creating a new skill. Based on the [Agent Skills specification](https://agentskills.io/specification) and [Claude Code skills docs](https://code.claude.com/docs/en/skills).

## Folder Structure

```markdown
skill-name/
├── SKILL.md                      # Core instructions (under 500 lines)
├── references/                   # Documentation loaded on demand
│   ├── example_[type].md
│   └── spec_[topic].md
├── scripts/                      # Executable code
│   └── script_[purpose].py
├── assets/                       # Static resources, schemas
│   └── template_[type].md
└── templates/                    # Alternative template location
    └── template_[type].md
```

## SKILL.md Template (Minimal)

````markdown
---
name: skill-name
description: "[What the skill does]. Use when [specific contexts, including non-obvious ones]. Triggers on: [trigger1], [trigger2], [trigger3]."
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

This skill's SOLE responsibility is [primary function].

## Checklist

Before completing, verify:

- [ ] [Verification step 1]
- [ ] [Verification step 2]
- [ ] [Verification step 3]
- [ ] Saved output to [location]
- [ ] Did NOT [stopping rule violation]

````

## SKILL.md Template (Full — with Claude Code Extensions)

````markdown
---
name: skill-name
description: "[What the skill does]. Use when [specific contexts]. Triggers on: [trigger1], [trigger2]."
# --- Optional Claude Code fields ---
# argument-hint: "[required-arg] [optional-arg]"
# disable-model-invocation: true     # Only user can invoke via /skill-name
# user-invocable: false              # Only Claude can invoke (background knowledge)
# allowed-tools: Read, Grep, Bash    # Tools permitted without asking
# context: fork                      # Run in isolated subagent
# agent: Explore                     # Subagent type (Explore, Plan, custom)
# model: sonnet                      # Override model
# effort: high                       # Override effort level
# paths: "src/api/**/*.ts"           # Only activate for matching files
# shell: powershell                  # Shell for !`cmd` blocks on Windows
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

This skill's SOLE responsibility is [primary function].

## Checklist

Before completing, verify:

- [ ] [Verification step 1]
- [ ] [Verification step 2]
- [ ] [Verification step 3]
- [ ] Saved output to [location]
- [ ] Did NOT [stopping rule violation]

````

## SKILL.md Template (Task with Arguments)

````markdown
---
name: fix-issue
description: "Fix a GitHub issue by number. Use when asked to fix, resolve, or address a specific issue."
disable-model-invocation: true
argument-hint: "[issue-number]"
---

Fix GitHub issue $ARGUMENTS following our coding standards.

1. Read the issue description
2. Understand the requirements
3. Implement the fix
4. Write tests
5. Create a commit

````

## SKILL.md Template (Subagent Research)

````markdown
---
name: deep-research
description: "Research a topic thoroughly across the codebase. Use when asked to investigate, explore, or understand a topic in depth."
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:

1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references

````

## Quick Checklist for New Skills

Before publishing:

- [ ] Folder name = `name` field (lowercase, hyphens)
- [ ] Description front-loads key use case in first 250 chars
- [ ] Description includes trigger keywords and specific contexts
- [ ] SKILL.md under 500 lines / < 5,000 tokens
- [ ] Large reference material in `references/` or `assets/`
- [ ] Reference files are 1 level deep
- [ ] Reference files 100+ lines have TOC
- [ ] Conditional cues tell agent when to load each file
- [ ] No time-sensitive information
- [ ] Consistent terminology throughout
- [ ] All file paths use forward slashes
- [ ] Stopping rules defined
- [ ] Completion checklist included
- [ ] Tested with representative queries
