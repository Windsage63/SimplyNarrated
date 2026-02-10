# Progressive Disclosure

How to organize skill content across multiple files for efficient context loading.

---

## The Three-Level System

Claude loads skill content progressively:

| Level | Content | When Loaded | Size |
| ----- | ------- | ----------- | ---- |
| 1 | `name` + `description` | Always (startup) | ~100 tokens |
| 2 | SKILL.md body | On skill trigger | Up to 5,000 words |
| 3 | Reference files | On explicit need | Unlimited |

---

## When to Extract to Reference Files

### Extract When

- **Large examples** (50+ lines of code/output)
- **Complete templates** (full file structures)
- **Detailed specifications** (API schemas, format specs)
- **Variant-specific content** (language-specific instructions)
- **Historical context** (changelog, migration guides)

### Keep Inline When

- **Brief examples** (under 20 lines)
- **Core workflow steps** (always needed)
- **Quick reference tables** (frequently consulted)
- **Stopping rules and checklists** (critical constraints)

---

## File Organization

### Standard Structure

```markdown
skill-name/
├── SKILL.md                    # Core instructions (under 500 lines)
└── references/
    ├── example_[type].md       # Large examples
    ├── template_[type].md      # Output templates  
    └── spec_[topic].md         # Detailed specifications
```

### Naming Conventions

| Type | Pattern | Example |
| ---- | ------- | ------- |
| Examples | `example_[what].md` | `example_blueprint.md` |
| Templates | `template_[what].md` | `template_prd.md` |
| Specs | `spec_[topic].md` | `spec_api_format.md` |
| Guides | `guide_[topic].md` | `guide_migration.md` |

---

## Linking From SKILL.md

### Standard Pattern

```markdown
See [`references/example_blueprint.md`](references/example_blueprint.md) for a complete example.
```

### With Context

```markdown
## Complete Example

See [`references/example_blueprint.md`](references/example_blueprint.md) for a realistic completed architectural blueprint (TaskFlow example).
```

### Conditional Loading

```markdown
## Advanced Configuration

For complex multi-environment setups, see [`references/advanced_config.md`](references/advanced_config.md).
```

---

## Critical Rule: No Deep Nesting

Reference files must be **one level deep** from SKILL.md.

### ✅ Correct

```markdown
SKILL.md → references/example.md
```

### ❌ Incorrect

```markdown
SKILL.md → references/example.md → references/sub/detail.md
```

**Why:** Claude may only partially read deeply nested references, leading to incomplete context.

---

## Reference File Structure

Each reference file should be self-contained:

```markdown
# [Title]

Brief description of what this file contains.

---

## [Section 1]

Content...

## [Section 2]

Content...
```

**Do NOT include:**

- Frontmatter (not needed for reference files)
- Links back to SKILL.md (circular)
- Links to other reference files (nesting)
