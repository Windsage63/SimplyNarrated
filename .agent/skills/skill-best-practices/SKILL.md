---
name: skill-best-practices
description: "Guides the creation of Agent Skills following best practices, when creating, reviewing, or improving skills. Triggers on: create skill, review the skill, new skill, skill guidelines, skill best practices, write a skill."
---

# Skill Best Practices

Build skills that follow the [Agent Skills](https://agentskills.io/) open standard and Anthropic's official guidelines for discovery, structure, and progressive disclosure. Skills work across Claude Code, VS Code Copilot, Cursor, and other compatible agents.

## The Job

1. Review the skill's purpose and triggers with the user
2. Create skill folder: `.agent/skills/[skill-name]/` (or `.claude/skills/` for Claude Code)
3. Write `SKILL.md` with compliant frontmatter and body
4. Extract large examples/schemas to `references/` or `assets/` if needed
5. Verify line count, structure, and description quality
6. Test triggering with representative queries

## Quick Reference

| Element           | Constraint                                                              |
| ----------------- | ----------------------------------------------------------------------- |
| `name`            | Max 64 chars, lowercase letters/numbers/hyphens only, must match folder |
| `description`     | Max 1024 chars (front-load key use case in first 250 chars)             |
| Body length       | Under 500 lines / < 5,000 tokens                                        |
| Reference nesting | Max 1 level deep from SKILL.md                                          |

## Frontmatter Rules

YAML frontmatter between `---` markers. The open standard requires `name` and `description`. Claude Code makes all fields optional (uses directory name if `name` omitted). See the Quick Reference table above for hard constraints on `name` and `description`.

Read [`references/frontmatter_spec.md`](references/frontmatter_spec.md) when writing or troubleshooting frontmatter — it covers name validation rules, description writing patterns with good/bad examples, Claude Code extension fields (`allowed-tools`, `context`, `paths`, `hooks`, `$ARGUMENTS`, etc.), and discovery behavior.

## Skill Types

**Reference content** — Knowledge Claude applies to current work (conventions, patterns, style guides). Runs inline alongside conversation context.

**Task content** — Step-by-step instructions for a specific action (deployments, commits, code generation). Often invoked with `/skill-name`. Add `disable-model-invocation: true` if side effects are involved.

## Body Content Rules

### Core Principles

- **Assume Claude is smart** — only add what Claude doesn't already know
- **Question every line** — does this justify its token cost?
- **Examples over explanations** — show, don't tell
- **No duplication** — information in one place only
- **Match specificity to fragility** — prescriptive for fragile ops, flexible for creative tasks
- **Provide defaults, not menus** — pick one approach, mention alternatives briefly

### Structure Requirements

- **Under 500 lines / < 5,000 tokens**
- **Clear workflow** — numbered steps preferred
- **Stopping rules** — explicit "don't do X" section
- **Completion checklist** — verification steps

### Named Content Patterns

| Pattern               | When to Use                                                |
| --------------------- | ---------------------------------------------------------- |
| Gotchas section       | Non-obvious facts that defy assumptions (keep in SKILL.md) |
| Template pattern      | When output format matters                                 |
| Checklist pattern     | Multi-step workflows with dependencies                     |
| Validation loop       | Quality-critical tasks (do → validate → fix → repeat)      |
| Plan-validate-execute | Batch or destructive operations                            |
| Conditional workflow  | Decision points with different paths                       |

Read [`references/body_guidelines.md`](references/body_guidelines.md) when writing body content, choosing a named content pattern, or setting up an evaluation-driven development workflow.

## Progressive Disclosure

Skills use three-level progressive disclosure:

1. **Metadata (always loaded):** `name` + `description` (~100 tokens)
2. **SKILL.md body (on trigger):** Full instructions (< 5,000 tokens)
3. **Reference files (on demand):** Loaded only when explicitly needed

### When to Extract

- Large code examples (50+ lines)
- Complete output templates
- Detailed schemas or specifications
- Domain-specific reference material
- Variant-specific instructions

### Key Rule: Tell the Agent WHEN to Load Each File

```markdown
# Good — conditional trigger

Read `references/api-errors.md` if the API returns a non-200 status code.

# Bad — vague pointer

See references/ for details.
```

### File Organization

```
skill-name/
├── SKILL.md              # Core instructions (under 500 lines)
├── references/           # Documentation loaded on demand
│   ├── example_[type].md
│   └── spec_[topic].md
├── scripts/              # Executable code (run, not loaded into context)
│   └── script_[purpose].py
├── assets/               # Templates, schemas, static resources
│   └── template_[type].md
└── templates/            # Alternative location for output templates
    └── template_[type].md
```

Read [`references/progressive_disclosure.md`](references/progressive_disclosure.md) when deciding how to split content across files, choosing between inline vs. extracted content, or organizing domain-specific reference material.

## Development Workflow

1. **Start from real expertise** — complete a task with Claude first, then extract the reusable pattern
2. **Build evaluations first** — create ~20 test queries before writing extensive docs
3. **Write minimal instructions** — just enough to address discovered gaps
4. **Test triggering** — verify description activates on the right prompts
5. **Iterate with execution traces** — observe how Claude navigates the skill, refine accordingly

Read [`references/body_guidelines.md`](references/body_guidelines.md) for the full evaluation-driven development methodology.

## Checklist

Before finalizing a skill:

- [ ] Folder name matches `name` field (lowercase, hyphens)
- [ ] Description front-loads key use case in first 250 chars
- [ ] Description includes trigger keywords and specific contexts
- [ ] SKILL.md under 500 lines / < 5,000 tokens
- [ ] Large examples extracted to `references/` or `assets/`
- [ ] Reference files are 1 level deep (no nesting)
- [ ] Conditional loading cues tell Claude when to read each file
- [ ] No time-sensitive information (use "old patterns" sections)
- [ ] Consistent terminology throughout
- [ ] All file paths use forward slashes (no backslashes)
- [ ] Stopping rules clearly defined
- [ ] Completion checklist included

## Template

Read [`references/skill_template.md`](references/skill_template.md) when creating a new skill from scratch and need a copy-paste starter.
