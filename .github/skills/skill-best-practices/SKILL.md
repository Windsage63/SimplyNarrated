---
name: skill-best-practices
description: "Guides creation of Anthropic-compliant Claude skills. Triggers on: create skill, new skill, skill guidelines, skill best practices, write a skill."
---

# Skill Best Practices

Build Claude skills that follow Anthropic's official guidelines for discovery, structure, and progressive disclosure.

## Table of Contents

1. [The Job](#the-job)
2. [Quick Reference](#quick-reference)
3. [Frontmatter Rules](#frontmatter-rules)
4. [Body Content Rules](#body-content-rules)
5. [Progressive Disclosure](#progressive-disclosure)
6. [Checklist](#checklist)

---

## The Job

1. Review the skill's purpose and triggers with the user
2. Create skill folder: `.github/skills/[skill-name]/`
3. Write `SKILL.md` with compliant frontmatter and body
4. Extract large examples/schemas to `references/` if needed
5. Verify line count and structure

---

## Quick Reference

| Element | Constraint |
| ------- | ---------- |
| `name` | Max 64 chars, lowercase letters/numbers/hyphens only |
| `description` | Max 200 chars recommended, include trigger phrases |
| Body length | Under 500 lines / 5,000 words |
| TOC required | Files over 100 lines |
| Reference nesting | Max 1 level deep from SKILL.md |

---

## Frontmatter Rules

Every skill requires YAML frontmatter with `name` and `description`.

### Name Field

- **Max 64 characters**
- **Lowercase only** — no uppercase letters
- **Allowed:** letters, numbers, hyphens
- **Forbidden:** XML tags, reserved words ("anthropic", "claude")
- **Must match** the folder name

### Description Field

- **Max 200 characters** (recommended for efficient discovery)
- **Third-person voice** — injected into system prompt
- **Include trigger keywords** at the end
- **Focus:** What the skill does + when to use it

**Pattern:**

```yaml
"[What it does in one sentence]. Triggers on: [keyword 1], [keyword 2], [keyword 3]."
```

**Example:**

```yaml
description: "Generates PRDs with user stories and acceptance criteria. Triggers on: create prd, plan feature, write requirements."
```

See [`references/frontmatter_spec.md`](references/frontmatter_spec.md) for full specification.

---

## Body Content Rules

### Conciseness Principles

- **Assume Claude is smart** — only add novel context
- **Question every line** — does this justify its token cost?
- **No duplication** — information in one place only
- **Examples over explanations** — show, don't tell

### Structure Requirements

- **Under 500 lines / 5,000 words**
- **Add TOC** for files over 100 lines
- **Clear workflow** — numbered steps preferred
- **Stopping rules** — explicit "don't do X" section
- **Completion checklist** — verification steps

See [`references/body_guidelines.md`](references/body_guidelines.md) for detailed patterns.

---

## Progressive Disclosure

Claude loads content in three levels:

1. **Metadata (always loaded):** `name` + `description` (~100 tokens)
2. **SKILL.md body (on trigger):** Full instructions (up to 5,000 words)
3. **Reference files (on demand):** Loaded only when needed

### When to Extract to References

- Large code examples (50+ lines)
- Complete output templates
- Detailed schemas or specifications
- Variant-specific instructions

### File Organization

```markdown
skill-name/
├── SKILL.md              # Core instructions
└── references/
    ├── example.md        # Large example
    ├── template.md       # Output template
    └── spec.md           # Detailed specification
```

See [`references/progressive_disclosure.md`](references/progressive_disclosure.md) for patterns.

---

## Checklist

Before finalizing a skill:

- [ ] Folder name matches `name` field (lowercase, hyphens)
- [ ] Description under 200 chars with trigger keywords
- [ ] SKILL.md under 500 lines
- [ ] TOC added if over 100 lines
- [ ] Large examples extracted to `references/`
- [ ] Reference files are 1 level deep (no nesting)
- [ ] Stopping rules clearly defined
- [ ] Completion checklist included

---

## Template

See [`references/skill_template.md`](references/skill_template.md) for a ready-to-copy starter template.
