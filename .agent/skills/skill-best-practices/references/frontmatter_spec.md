# Frontmatter Specification

Complete rules for SKILL.md frontmatter fields, covering both the [Agent Skills open standard](https://agentskills.io/specification) and [Claude Code extensions](https://code.claude.com/docs/en/skills).

## Required Fields (Open Standard)

The open standard requires `name` and `description`. Claude Code makes all fields optional (uses directory name if `name` omitted, uses first paragraph if `description` omitted).

```yaml
---
name: skill-name
description: "What this skill does. Use when [specific contexts]. Triggers on: keyword1, keyword2."
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

The description is **not documentation** — it's a **trigger mechanism**. At startup, agents load only the `name` and `description` of all skills. The description carries the entire burden of deciding when to load the full SKILL.md.

**Key principles:**

1. **Front-load the key use case** — the first 250 characters are critical (rest may be truncated)
2. **Use imperative phrasing** — "Use when..." rather than "This skill does..."
3. **Be specific and pushy** — explicitly list contexts, including non-obvious ones
4. **Include action keywords** — verbs the user would naturally say
5. **Keep concise** — a few sentences to a short paragraph
6. **Avoid first/second person** — descriptions are injected into system prompt context

### Description Pattern

```yaml
"[What the skill does]. Use when [specific contexts, including non-obvious ones]. Triggers on: [keyword1], [keyword2], [keyword3]."
```

### Good Examples

```yaml
description: "Generates PRDs with user stories and acceptance criteria. Use when planning a new feature or writing requirements. Triggers on: create prd, plan feature, write requirements."

description: "Reviews code changes for correctness, security, and maintainability. Use when reviewing a pull request or checking code quality. Triggers on: review code, code review, check this PR."

description: "Analyze CSV and tabular data files — compute summary statistics, add derived columns, generate charts, and clean messy data. Use when the user has a CSV, TSV, or Excel file and wants to explore, transform, or visualize the data, even if they don't explicitly mention CSV or analysis."
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

## Claude Code Extension Fields

These fields are **Claude Code-specific** and extend the open standard:

### Invocation Control

| Field                      | Default | Purpose                                              |
| -------------------------- | ------- | ---------------------------------------------------- |
| `disable-model-invocation` | `false` | Set `true` to prevent Claude from auto-loading skill |
| `user-invocable`           | `true`  | Set `false` to hide from `/` menu                    |

**How they interact:**

| Configuration                     | User invocable? | Claude auto-loads? | Description in context? |
| --------------------------------- | --------------- | ------------------ | ----------------------- |
| (default)                         | Yes             | Yes                | Yes                     |
| `disable-model-invocation: true`  | Yes             | No                 | No                      |
| `user-invocable: false`           | No              | Yes                | Yes                     |

Use `disable-model-invocation: true` for workflows with side effects (deploy, commit, send messages). Use `user-invocable: false` for background knowledge users shouldn't invoke directly.

### Arguments

| Field           | Purpose                                                  |
| --------------- | -------------------------------------------------------- |
| `argument-hint` | Hint shown during autocomplete (e.g., `[issue-number]`)  |

**Substitution variables:**

| Variable               | Description                                        |
| ---------------------- | -------------------------------------------------- |
| `$ARGUMENTS`           | All arguments passed when invoking the skill       |
| `$ARGUMENTS[N]` / `$N` | Access specific argument by 0-based index          |
| `${CLAUDE_SESSION_ID}` | Current session ID                                 |
| `${CLAUDE_SKILL_DIR}`  | Directory containing the skill's SKILL.md          |

### Execution Context

| Field     | Purpose                                                              |
| --------- | -------------------------------------------------------------------- |
| `context` | Set to `fork` to run in an isolated subagent                         |
| `agent`   | Subagent type when `context: fork` (e.g., `Explore`, `Plan`, custom) |
| `model`   | Model to use when skill is active                                    |
| `effort`  | Override session effort (`low`, `medium`, `high`, `max`)             |

### Tool and Path Restrictions

| Field           | Purpose                                                 |
| --------------- | ------------------------------------------------------- |
| `allowed-tools` | Tools permitted without asking when skill is active     |
| `paths`         | Glob patterns limiting when skill auto-activates        |

### Lifecycle

| Field   | Purpose                                            |
| ------- | -------------------------------------------------- |
| `hooks` | Hooks scoped to this skill's lifecycle             |
| `shell` | Shell for `!`cmd`` blocks (`bash` or `powershell`) |

### Example with Extension Fields

```yaml
---
name: deploy
description: "Deploy the application to production. Use only when explicitly asked to deploy."
disable-model-invocation: true
argument-hint: "[environment]"
allowed-tools: Bash(git *), Bash(npm *)
---

Deploy $ARGUMENTS to production:
1. Run the test suite
2. Build the application
3. Push to the deployment target
```

## Open Standard Optional Fields

These fields are defined by the [Agent Skills specification](https://agentskills.io/specification):

| Field           | Purpose                                              |
| --------------- | ---------------------------------------------------- |
| `license`       | License name or reference to bundled license file    |
| `compatibility` | Max 500 chars. Environment requirements              |
| `metadata`      | Arbitrary key-value map for additional metadata      |
| `allowed-tools` | Space-delimited list of pre-approved tools           |

```yaml
---
name: pdf-processing
description: "Extract PDF text, fill forms, merge files. Use when handling PDFs."
license: Apache-2.0
compatibility: Requires Python 3.12+ and pdfplumber
metadata:
  author: example-org
  version: "1.0"
---
```

## Discovery Behavior

1. At startup, agent loads **only** `name` and `description` of all skills
2. Skill descriptions share a character budget (1% of context window, min 8,000 chars)
3. Each description is capped at **250 characters** in the listing regardless of budget
4. When a request matches, the **full SKILL.md body** is loaded
5. Reference files are loaded only when the agent determines they're needed
6. Skills with `disable-model-invocation: true` have descriptions **removed** from context entirely

**Implication:** Front-load the most important information in the first 250 characters of your description. Everything needed for discovery must be there.
