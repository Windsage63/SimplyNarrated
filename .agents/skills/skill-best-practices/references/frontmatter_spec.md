# Frontmatter Specification

Rules for SKILL.md frontmatter fields.

## Core Fields

To create skills that are portable across different agents, use only `name` and `description` in `SKILL.md` frontmatter.

```yaml
---
name: skill-name
description: "What this skill does, when [specific contexts]. Triggers on: keyword1, keyword2."
---
```

## Discovery Behavior

1. The agent discovers skill folders that contain `SKILL.md`
2. The agent reads `name` and `description` first
3. The agent chooses whether to load the full skill based primarily on the first 250 characters of the `description`
4. Reference files are loaded only when the body clearly points to them

**Implication:** Front-load the most important information in the first 250 characters of your description. Everything needed for discovery **must** be there.

## Template

Use this exact frontmatter shape for skills:

```yaml
---
name: skill-name
description: "[What the skill does], when [specific contexts]. Triggers on: [keyword1], [keyword2], [keyword3]."
---
```

## Name Field Rules

| Rule                 | Constraint                                    |
| -------------------- | --------------------------------------------- |
| Max length           | 64 characters                                 |
| Allowed characters   | Lowercase letters, numbers, hyphens           |
| Must match           | Folder name exactly                           |
| Cannot start/end     | With hyphens                                  |
| Cannot contain       | Consecutive hyphens (`--`)                    |
| Forbidden            | XML tags, "anthropic", "claude"               |

### Naming Conventions

**Prefer gerund form** (verb + -ing) for names that describe an activity:

```yaml
name: processing-pdfs
name: analyzing-spreadsheets
name: writing-documentation
```

**Noun phrases** and **action-oriented** names are also acceptable:

```yaml
name: code-review
name: docs-sync
name: project-pipeline
```

**Avoid:**

  - Vague names: `helper`, `utils`, `tools`
  - Overly generic: `documents`, `data`, `files`
  - Reserved words: `anthropic-helper`, `claude-tools`
  - Inconsistent patterns within your skill collection

### Valid Examples

```yaml
name: code-review
name: docs-sync
name: project-pipeline
name: html-wsl
name: processing-pdfs
```

### Invalid Examples

```yaml
name: Code-Review      # uppercase
name: code_review      # underscore
name: -code-review     # starts with hyphen
name: code--review     # consecutive hyphens
name: claude-helper    # reserved word
name: code<review>     # XML tags
```

## Description Field Rules

| Rule               | Constraint                                              |
| ------------------ | ------------------------------------------------------- |
| Max length         | 1024 characters (hard limit)                            |
| Truncation         | Skill listing truncates at 250 characters               |
| Cannot contain     | XML tags                                                |
| Purpose            | Skill discovery and triggering                          |
| Budget             | Dynamic at 1% of context window (fallback: 8,000 chars) |

### Writing Effective Descriptions

The description is **not documentation** - it's a **trigger mechanism**. At startup, agents load only the `name` and `description` of all skills. The description carries the entire burden of deciding when to load the full SKILL.md.

**Key principles:**

1. **Front-load the key use case** - the first 250 characters are critical (rest may be truncated)
2. **Use imperative phrasing** - "Use when..." rather than "This skill does..."
3. **Be specific and pushy** - explicitly list contexts, including non-obvious ones
4. **Include action keywords** - verbs the user would naturally say
5. **Keep concise** - a few sentences to a short paragraph
6. **Avoid first/second person** - descriptions are injected into system prompt context

### Description Pattern

```yaml
description: "[What the skill does], when [specific contexts, including non-obvious ones]. Triggers on: [keyword1], [keyword2], [keyword3]."
```

### Good Examples

```yaml
description: "Generates PRDs with user stories and acceptance criteria, when planning a new feature or writing requirements. Triggers on: create prd, plan feature, write requirements."

description: "Reviews code changes for correctness, security, and maintainability, when reviewing a pull request or checking code quality. Triggers on: review code, code review, check this PR."

description: "Analyze CSV and tabular data files - compute summary statistics, add derived columns, generate charts, and clean messy data, when the user has a CSV, TSV, or Excel file and wants to explore, transform, or visualize the data, even if they don't explicitly mention CSV or analysis."
```

### Bad Examples

```yaml
# Too vague, no triggers
description: "A skill for handling code."

# First-person voice
description: "I review code and provide feedback."

# Too long, buried triggers, key use case not front-loaded
description: "This comprehensive skill provides detailed code review capabilities including security analysis, performance optimization suggestions, maintainability improvements, and style corrections. It can be used when you want to review code."

# Too terse
description: "Helps with documents."
```
