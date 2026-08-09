---
name: skill-best-practices
description: "Guides creation, review, and improvement of portable Agent Skills that work across Codex, Claude Code, GitHub Copilot, Antigravity, and other compatible agents. Triggers on: create skill, review skill, new skill, skill guidelines, skill best practices, write a skill."
---

# Skill Best Practices

Build skills that follow the [Agent Skills](https://agentskills.io/) open standard for discovery, structure, and progressive disclosure. Skills should be agent agnostic: write `SKILL.md` content that can be understood by different coding agents without relying on one agent's private tools, metadata, memory, plugins, or approval model.

## The Job

1. Understand the skill's purpose, target agents, user prompts, and expected outputs
2. Create or update the portable skill folder at `.agents/skills/[skill-name]/`
3. Write `SKILL.md` with compliant frontmatter, concise body instructions, stopping rules, and a checklist
4. Extract large examples, schemas, variant details, and templates to `references/`, `assets/`, `scripts/`, or `templates/` when useful
5. Validate structure, portability, description quality, and progressive-disclosure links
6. Test triggering and task execution with representative prompts, then iterate from observed failures

## Quick Reference

| Element           | Constraint                                                              |
| ----------------- | ----------------------------------------------------------------------- |
| `name`            | Max 64 chars, lowercase letters/numbers/hyphens only, must match folder |
| `description`     | Max 1024 chars; front-load key use case in first 250 chars              |
| Body length       | Under 500 lines / < 5,000 tokens                                        |
| Reference nesting | Max 1 level deep from SKILL.md                                          |
| Default location  | `.agents/skills/[skill-name]/`                                          |

## Frontmatter Rules

YAML frontmatter belongs between `---` markers. Include only `name` and `description`, while adhering to the Quick Reference table above for hard constraints.

Read [`references/frontmatter_spec.md`](references/frontmatter_spec.md) when writing or troubleshooting frontmatter. It covers required fields, name validation rules, description writing patterns with good/bad examples, and discovery behavior.

## Skill Types

**Reference content** - Knowledge the agent applies to current work: conventions, patterns, schemas, or style guides. It runs inline alongside conversation context.

**Task content** - Step-by-step instructions for a specific action: deployments, commits, code generation, document processing. For side-effecting workflows, include explicit invocation and approval guidance in the body without assuming a specific host agent.

## Body Content Rules

### Core Principles

- **Assume the agent is smart** - only add what the agent does not already know
- **Question every line** - does this justify its token cost?
- **Examples over explanations** - show, do not over-explain
- **No duplication** - information in one place only
- **Match specificity to fragility** - prescriptive for fragile operations, flexible for creative tasks
- **Provide defaults, not menus** - pick one approach, mention alternatives briefly
- **Stay portable** - avoid host-specific UI labels, plugin names, shell assumptions, or metadata unless marked optional

### Structure Requirements

- **Under 500 lines / < 5,000 tokens**
- **Clear workflow** - numbered steps preferred
- **Stopping rules** - explicit "do not do X" section
- **Completion checklist** - verification steps
- **Portable paths** - use forward slashes in examples, even on Windows

### Named Content Patterns

| Pattern               | When to Use                                                |
| --------------------- | ---------------------------------------------------------- |
| Gotchas section       | Non-obvious facts that defy assumptions; keep in SKILL.md  |
| Template pattern      | When output format matters                                 |
| Checklist pattern     | Multi-step workflows with dependencies                     |
| Validation loop       | Quality-critical tasks: do -> validate -> fix -> repeat    |
| Plan-validate-execute | Batch or destructive operations                            |
| Conditional workflow  | Decision points with different paths                       |

Read [`references/body_guidelines.md`](references/body_guidelines.md) when writing body content, choosing a named content pattern, or setting up an evaluation-driven development workflow.

## Progressive Disclosure

Skills use three-level progressive disclosure:

1. **Metadata, always loaded:** `name` + `description` (~100 tokens)
2. **SKILL.md body, on trigger:** full instructions (< 5,000 tokens)
3. **Reference files, on demand:** loaded only when explicitly needed

### When to Extract

- Large code examples: 50+ lines
- Complete output templates
- Detailed schemas or specifications
- Domain-specific reference material
- Variant-specific instructions

### Key Rule: Tell the Agent WHEN to Load Each File

```markdown
# Good - conditional trigger

Read `references/api-errors.md` if the API returns a non-200 status code.

# Bad - vague pointer

See references/ for details.
```

### File Organization

```text
skill-name/
|-- SKILL.md              # Core instructions; under 500 lines
|-- references/           # Documentation loaded on demand
|   |-- example_[type].md
|   `-- spec_[topic].md
|-- scripts/              # Executable code; run, not loaded into context
|   `-- script_[purpose].py
|-- assets/               # Templates, schemas, static resources
|   `-- template_[type].md
`-- templates/            # Alternative location for output templates
    `-- template_[type].md
```

Read [`references/progressive_disclosure.md`](references/progressive_disclosure.md) when deciding how to split content across files, choosing between inline vs. extracted content, or organizing domain-specific reference material.

## Development Workflow

1. **Gather examples first** - collect 3-5 realistic user prompts, expected outputs, and known failure modes
2. **Design the portable surface** - choose the skill name, trigger description, folder path, and resource layout without relying on one agent's private metadata
3. **Write the smallest useful skill** - document only the workflow, gotchas, default tools, stopping rules, and completion checks that change agent behavior
4. **Add resources deliberately** - put large examples, schemas, and variants in one-level reference files with clear load conditions
5. **Validate mechanically** - check folder/name match, frontmatter shape, description length, body length, links, reference depth, path separators, and encoding
6. **Evaluate behavior** - test 10 should-trigger prompts and 10 should-not-trigger prompts; for triggered prompts, verify the agent can complete the task using only the skill and task-local artifacts
7. **Iterate from traces** - refine instructions from observed misses, ignored references, overbroad triggering, or repeated agent confusion

Read [`references/body_guidelines.md`](references/body_guidelines.md) for the full evaluation-driven development methodology.

## Portable Validation

Use host-available tools rather than agent-specific validators. If a validator exists in the current environment, it may be used, but the skill must still pass this portable checklist:

1. **Structure:** `.agents/skills/[skill-name]/SKILL.md` exists and optional resource folders are one level below the skill root
2. **Frontmatter:** only `name` and `description` appear between `---` markers; `name` matches the folder and uses lowercase letters, numbers, and hyphens
3. **Description:** under 1024 characters, front-loads the use case in the first 250 characters, includes concrete trigger contexts, and avoids XML tags
4. **Body:** under 500 lines, avoids duplicated reference content, includes workflow, stopping rules, and checklist
5. **References:** every linked reference has a clear "when to read" condition; references do not link onward to deeper reference files
6. **Portability:** paths use forward slashes, instructions do not require a single agent's plugin, memory, UI metadata, or approval model unless stated as optional
7. **Rendering:** files are UTF-8 without BOM, tree examples use ASCII, and rendered text contains no mojibake or broken box-drawing characters
8. **Behavior:** representative prompts trigger the skill when they should, avoid triggering when they should not, and complete at least one realistic task without hidden context

## Checklist

Before finalizing a skill:

- [ ] Folder name matches `name` field: lowercase letters, numbers, hyphens
- [ ] Description front-loads key use case in first 250 chars
- [ ] Description includes trigger keywords and specific contexts
- [ ] SKILL.md is under 500 lines / < 5,000 tokens
- [ ] Large examples extracted to `references/`, `assets/`, `scripts/`, or `templates/`
- [ ] Reference files are 1 level deep; no nested reference chains
- [ ] Conditional loading cues tell the agent when to read each file
- [ ] No time-sensitive information unless placed in an "old patterns" section
- [ ] Consistent terminology throughout
- [ ] All file paths use forward slashes
- [ ] No host-specific assumptions unless optional and clearly labeled
- [ ] Stopping rules clearly defined
- [ ] Completion checklist included
- [ ] Representative trigger and non-trigger prompts tested
- [ ] Rendered markdown is free of encoding artifacts and broken tree characters

## Template

Read [`references/skill_template.md`](references/skill_template.md) when creating a new skill from scratch and need a copy-paste starter.
