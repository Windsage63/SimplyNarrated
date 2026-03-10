# Frontmatter Specification

Complete rules for SKILL.md frontmatter fields.

---

## Required Fields

Every `SKILL.md` must begin with YAML frontmatter containing exactly two fields:

```yaml
---
name: skill-name
description: "What this skill does. Triggers on: keyword1, keyword2."
---
```

---

## Name Field Rules

| Rule | Constraint |
| ---- | ---------- |
| Max length | 64 characters |
| Allowed characters | Lowercase letters, numbers, hyphens |
| Must match | Folder name exactly |
| Cannot start/end with | Hyphens |
| Cannot contain | Consecutive hyphens (`--`) |
| Forbidden | XML tags, "anthropic", "claude" |

### Valid Examples

```markdown
name: code-review
name: docs-sync
name: project-pipeline
name: html-wsl
```

### Invalid Examples

```markdown
name: Code-Review      # uppercase
name: code_review      # underscore
name: -code-review     # starts with hyphen
name: code--review     # consecutive hyphens
name: claude-helper    # reserved word
```

---

## Description Field Rules

| Rule | Constraint |
| ---- | ---------- |
| Max length | 1024 characters (200 recommended) |
| Cannot contain | XML tags |
| Voice | Third-person (injected into system prompt) |
| Purpose | Skill discovery and triggering |

### Writing Effective Descriptions

The description is **not documentation** — it's a **trigger mechanism**. Claude scans all skill descriptions at startup to decide which to load.

**Key principles:**

1. **Be specific and condition-based** — explicit triggers
2. **Include action keywords** — verbs the user might say
3. **Keep concise** — shorter = faster discovery
4. **Third-person voice** — "Generates..." not "Generate..."

### Description Pattern

```yaml
"[What the skill does in one sentence]. Triggers on: [trigger1], [trigger2], [trigger3]."
```

### Good Examples

```yaml
description: "Generates PRDs with user stories and acceptance criteria. Triggers on: create prd, plan feature, write requirements."

description: "Reviews code changes for correctness, security, and maintainability. Triggers on: review code, code review, check this PR."

description: "Maps WSL Linux file paths to Windows browser URLs. Triggers on: open in browser, preview html, wsl file path."
```

### Bad Examples

```yaml
# Too vague, no triggers
description: "A skill for handling code."

# First-person voice
description: "I review code and provide feedback."

# Too long, buried triggers
description: "This comprehensive skill provides detailed code review capabilities including security analysis, performance optimization suggestions, maintainability improvements, and style corrections. It can be used when you want to review code."
```

---

## Discovery Behavior

Claude's skill discovery works as follows:

1. At startup, Claude loads **only** `name` and `description` of all skills
2. When user makes a request, Claude scans descriptions for matches
3. If a description matches, the **full SKILL.md body** is loaded
4. Reference files are loaded only when explicitly needed

**Implication:** Everything needed for discovery must be in the description. The body is only read after triggering.
