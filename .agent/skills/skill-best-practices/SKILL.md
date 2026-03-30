---
name: skill-best-practices
description: "**WORKFLOW SKILL** — Guides creation of Agent Skills following the open standard and Anthropic best practices. Use whenever creating, reviewing, or improving skills. Triggers on: create skill, new skill, skill guidelines, skill best practices, write a skill."
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

| Element              | Constraint                                                              |
| -------------------- | ----------------------------------------------------------------------- |
| `name`               | Max 64 chars, lowercase letters/numbers/hyphens only, must match folder |
| `description`        | Max 1024 chars (front-load key use case in first 250 chars)             |
| Body length          | Under 500 lines / < 5,000 tokens                                        |
| Reference nesting    | Max 1 level deep from SKILL.md                                          |
| Reference files 100+ | Include table of contents at top                                        |

## Frontmatter Rules

YAML frontmatter between `---` markers. The open standard requires `name` and `description`. Claude Code makes all fields optional (uses directory name if `name` omitted).

### Name Field

- **Max 64 characters**, lowercase letters, numbers, hyphens only
- **Cannot** start/end with hyphens or contain consecutive hyphens (`--`)
- **Forbidden:** XML tags, reserved words ("anthropic", "claude")
- **Must match** the folder name
- **Prefer gerund form** (`processing-pdfs`, `analyzing-data`) or noun phrases (`code-review`)

### Description Field

- **Max 1024 characters** (hard limit); **first 250 chars are critical** (truncated in skill listing)
- **Front-load the key use case** — Claude uses descriptions to decide which skill to load
- **Imperative phrasing** — "Use when..." rather than "This skill does..."
- **Be specific and pushy** — list contexts where the skill applies, including non-obvious cases
- **Include trigger keywords** — terms users would naturally say

**Pattern:**

```yaml
description: "[What it does]. Use when [specific contexts, including non-obvious ones]. Triggers on: [keyword1], [keyword2], [keyword3]."
```

**Example:**

```yaml
description: "Generates PRDs with user stories and acceptance criteria. Use when planning a new feature, writing requirements, or scoping a refactor. Triggers on: create prd, plan feature, write requirements, spec out."
```

### Additional Frontmatter Fields (Claude Code)

Claude Code extends the open standard with optional fields for invocation control, execution context, and tool restrictions. See [`references/frontmatter_spec.md`](references/frontmatter_spec.md) for the complete reference.

Key fields: `disable-model-invocation`, `user-invocable`, `allowed-tools`, `context`, `agent`, `paths`, `argument-hint`, `model`, `effort`, `hooks`, `shell`.

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

See [`references/body_guidelines.md`](references/body_guidelines.md) for detailed patterns and examples.

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

See [`references/progressive_disclosure.md`](references/progressive_disclosure.md) for detailed patterns.

## Dynamic Features (Claude Code)

- **`$ARGUMENTS` / `$N`** — String substitution for arguments passed to skills
- **`!`command``** — Shell command preprocessing (runs before Claude sees content)
- **`context: fork`** — Run skill in an isolated subagent context
- **`"ultrathink"`** — Include this word in skill content to enable extended thinking

## Development Workflow

1. **Start from real expertise** — complete a task with Claude first, then extract the reusable pattern
2. **Build evaluations first** — create ~20 test queries before writing extensive docs
3. **Write minimal instructions** — just enough to address discovered gaps
4. **Test triggering** — verify description activates on the right prompts
5. **Iterate with execution traces** — observe how Claude navigates the skill, refine accordingly

See [`references/body_guidelines.md`](references/body_guidelines.md) for the full iterative development workflow.

## Checklist

Before finalizing a skill:

- [ ] Folder name matches `name` field (lowercase, hyphens)
- [ ] Description front-loads key use case in first 250 chars
- [ ] Description includes trigger keywords and specific contexts
- [ ] SKILL.md under 500 lines / < 5,000 tokens
- [ ] Large examples extracted to `references/` or `assets/`
- [ ] Reference files are 1 level deep (no nesting)
- [ ] Reference files 100+ lines have table of contents
- [ ] Conditional loading cues tell Claude when to read each file
- [ ] No time-sensitive information (use "old patterns" sections)
- [ ] Consistent terminology throughout
- [ ] All file paths use forward slashes (no backslashes)
- [ ] Stopping rules clearly defined
- [ ] Completion checklist included

## Template

See [`references/skill_template.md`](references/skill_template.md) for a ready-to-copy starter template.
