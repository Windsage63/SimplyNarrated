# Instruction Files for Dummies

A complete primer on the AI agent instruction file system — what each file type does, when to use it, and how they all work together.

---

## The Big Picture

AI coding agents (Copilot, Claude Code, Cursor, etc.) read instruction files to understand your project's rules, conventions, and preferences. Instead of repeating "always use async/await" in every chat prompt, you write it once in an instruction file and every agent follows it automatically.

There are two categories:

| Category | Files | When Loaded |
| --- | --- | --- |
| **Always-on** | `AGENTS.md` (primary), `CLAUDE.md` (compatibility) | Every single chat interaction, automatically |
| **File-based** | `*.instructions.md` | Only when relevant files are being edited, or the task matches |

Think of always-on instructions as the "constitution" of your project. File-based instructions are the "local ordinances" for specific neighborhoods.

---

## Your Always-On Foundation: `AGENTS.md`

This loads into every agent's context on **every** interaction, no matter what you're doing. Because it's always present, every line competes for the agent's limited attention (context window). Keep it lean.

| Property | Value |
| --- | --- |
| **Location** | Root of workspace (and optionally subfolders) |
| **Loaded** | Always, automatically |
| **Format** | Plain Markdown (no YAML frontmatter) |
| **Audience** | All AI coding agents (Copilot, Claude Code, Cursor, Windsurf, etc.) |

`AGENTS.md` is the **cross-agent open standard**. One file, recognized by every major AI coding tool. It's the best starting point for any project.

### Why AGENTS.md over copilot-instructions.md

VS Code also supports `.github/copilot-instructions.md` — a Copilot-specific equivalent. Both work the same way (always-on, plain Markdown, no frontmatter), but `AGENTS.md` has clear advantages:

| | `AGENTS.md` | `copilot-instructions.md` |
| --- | --- | --- |
| **Works with** | All AI agents | Copilot only |
| **Subfolder hierarchy** | Yes (monorepo support) | No |
| **Location** | Workspace root (visible) | Hidden in `.github/` |
| **Standard** | Open cross-agent standard | Copilot-specific |

**Pick one, never both.** If both exist, VS Code loads both but behavior is undefined when they conflict. If you're migrating from `copilot-instructions.md`, move the content to `AGENTS.md` and delete the old file.

### What belongs in AGENTS.md

  - **Project overview** — 2-3 sentences about what the app does, primary tech stack
  - **Commands** — Exact, verified commands to run, test, and build the project
  - **Architecture** — Source directory tree with one-line descriptions
  - **Key conventions** — Patterns unique to *this* project that the agent would get wrong without being told (singleton patterns, error handling flows, file headers, async rules)
  - **Environment quirks** — Embedded runtimes, vendored dependencies, non-standard setups

### What does NOT belong in AGENTS.md

  - Standard language conventions (PEP 8, ESLint defaults) — agents already know these
  - Rules enforced by linters/formatters — don't duplicate automation
  - Copy of your README — agents can read it when needed; link instead
  - File-specific rules — those belong in `.instructions.md` files
  - Long API documentation — link to `docs/` instead of embedding

### Example

```markdown
# MyProject

## Project Overview

MyProject is a FastAPI REST API for inventory management with PostgreSQL. Python 3.12, SQLAlchemy 2.0 async, Alembic migrations.

## Commands

### Run
python -m uvicorn src.main:app --reload --port 8000

### Test
python -m pytest tests/ -m "not slow"

## Architecture

src/
├── main.py          # App factory, middleware, lifespan
├── api/routes.py    # All HTTP endpoints (single router)
├── core/            # Business logic modules
└── models/          # SQLAlchemy ORM + Pydantic schemas

## Key Conventions

### Service access pattern
Core services are singletons accessed via module-level getters:
from src.core.job_manager import get_job_manager
jm = get_job_manager()

### Async throughout
All route handlers use async def + aiofiles. CPU-bound work goes to thread pool:
await asyncio.get_event_loop().run_in_executor(None, blocking_fn)

### File headers
Every Python module starts with:
"""
@fileoverview [Description]
@author Name <email>
@license Apache-2.0
"""
```

### Subfolder Hierarchy (Monorepo Support)

The killer feature of `AGENTS.md` is subfolder overrides. The closest file to the code being edited takes precedence:

```markdown
/AGENTS.md                  # Root defaults (applies everywhere)
/frontend/AGENTS.md         # Frontend-specific (overrides root for frontend/)
/backend/AGENTS.md          # Backend-specific (overrides root for backend/)
/backend/api/AGENTS.md      # Even more specific
```

This means you can have project-wide commands and conventions in the root, then layer on frontend-specific React rules or backend-specific API conventions without bloating the root file.

> **Note:** Nested `AGENTS.md` files require the `chat.useNestedAgentsMdFiles` setting to be enabled in VS Code.

---

### Compatibility: `CLAUDE.md`

| Property | Value |
| --- | --- |
| **Location** | Workspace root, `.claude/CLAUDE.md`, or `~/.claude/CLAUDE.md` |
| **Loaded** | Always, automatically (if `chat.useClaudeMdFile` is enabled) |
| **Audience** | Claude Code and Claude-based tools |

If you also use Claude Code, it has its own `CLAUDE.md` format. VS Code reads this file too, so you don't need to duplicate its content into `AGENTS.md`. Keep Claude-specific rules in `CLAUDE.md` and shared rules in `AGENTS.md`.

There's also `CLAUDE.local.md` for local-only rules you don't want committed to version control.

---

## The File-Based Instructions

### `*.instructions.md`

| Property | Value |
| --- | --- |
| **Location** | `.github/instructions/` (workspace) or `~/.copilot/instructions/` (user) |
| **Loaded** | Conditionally — when `applyTo` matches or `description` matches the task |
| **Format** | Markdown with optional YAML frontmatter |
| **Best for** | Language-specific, framework-specific, or folder-specific rules |

These are the **targeted rules** that only load when relevant. They don't waste context budget on every interaction — they activate only when the agent is working with matching files or tasks.

#### Frontmatter controls when they load

```yaml
---
name: "Python Standards"          # Optional display name
description: "Use when writing Python files. Covers import ordering and type hints."
applyTo: "**/*.py"                # Glob pattern for automatic application
---
```

There are three discovery modes:

| Mode | Frontmatter | When It Loads |
| --- | --- | --- |
| **Explicit** | `applyTo: "**/*.py"` | Agent creates or modifies a `.py` file |
| **On-demand** | `description: "Use when..."` | Agent detects task relevance from description |
| **Both** | `applyTo` + `description` | Either trigger fires |
| **Manual** | Neither | Only when you manually attach it via "Add Context" |

> **Important:** `applyTo` only triggers when the agent is **creating or modifying** matching files, not when just reading them.

#### File locations

VS Code searches these directories recursively:

```markdown
.github/instructions/          # Workspace (team-shared, committed)
.claude/rules/                 # Claude format (workspace)
~/.copilot/instructions/       # User profile (personal, cross-workspace)
~/.claude/rules/               # Claude format (user profile)
```

You can organize in subdirectories:

```markdown
.github/instructions/
  frontend/
    react.instructions.md
    accessibility.instructions.md
  backend/
    api-design.instructions.md
    database.instructions.md
  testing/
    unit-tests.instructions.md
```

#### Example: Python testing conventions

````markdown
---
description: "Use when writing or modifying test files. Covers test naming, fixtures, and assertions."
applyTo: "tests/**"
---
# Test Conventions

- Name test files `test_{module}.py`
- Use fixtures from `conftest.py` — don't duplicate setup
- Use `pytest.raises` for expected exceptions

Preferred:
```python
def test_upload_rejects_invalid_format(mock_library):
    with pytest.raises(ValueError, match="unsupported format"):
        upload_file("data.xyz", mock_library)
```

Avoid:

```python
def test_upload():
    try:
        upload_file("data.xyz", lib)
        assert False
    except:
        pass
```
````

#### Example: Frontend DOM safety

```markdown
---
description: "Use when creating or modifying frontend JavaScript."
applyTo: "static/js/**"
---
# Frontend Patterns

- Escape all user-provided text before inserting into DOM
- Use `textContent` not `innerHTML` for user data
- Use event delegation on containers, not listeners on individual items
```

#### Example: On-demand (no applyTo)

```markdown
---
description: "Use when writing database migrations or modifying schemas."
---
# Migration Guidelines

- Always create reversible migrations
- Never drop columns in the same release as code removal
- Test the rollback path before merging
```

This loads only when the agent determines a task involves migrations — regardless of which files are open.

---

## How They All Fit Together

Here's the complete hierarchy, from broadest to most targeted:

```markdown
┌─────────────────────────────────────────────────┐
│  Organization Instructions                       │  Broadest scope
│  (GitHub org level, lowest priority)             │  (optional)
├─────────────────────────────────────────────────┤
│  Always-On Workspace Instructions                │
│  AGENTS.md (root and/or subfolders)              │  Every interaction
│                                                  │
├─────────────────────────────────────────────────┤
│  File-Based Instructions                         │
│  .github/instructions/*.instructions.md          │  Only when relevant
│  (loaded by applyTo or description match)        │
├─────────────────────────────────────────────────┤
│  User Instructions                               │  Highest priority
│  ~/.copilot/instructions/*.instructions.md       │  Personal preferences
└─────────────────────────────────────────────────┘
```

### Priority when they conflict

1. **Personal** (user-level) — highest priority
2. **Repository** (`AGENTS.md`) — middle
3. **Organization** — lowest priority

When multiple instruction files apply at the same level, VS Code merges them all into the context. There's no guaranteed order, so don't rely on one overriding another.

---

## Decision Flowchart

```markdown
Does this rule apply to EVERY task in the project?
├── Yes → Put it in AGENTS.md (root)
│
└── No  → Does it apply to a specific folder in a monorepo?
          ├── Yes → Put it in a subfolder AGENTS.md
          └── No  → Does it apply to specific file types?
                    ├── Yes → .instructions.md with applyTo
                    └── No  → .instructions.md with description (on-demand)
```

**The recommended progression:**

1. Start with `AGENTS.md` — project overview, commands, architecture, key conventions
2. As the project grows, add `.instructions.md` files for specific concerns — testing rules, API patterns, frontend conventions
3. If you have personal preferences that span all projects, add user-level `.instructions.md` files in `~/.copilot/instructions/`

---

## Quick Rules of Thumb

1. **Keep always-on files lean.** They load every time. A 500-line instructions file burns context on every trivial question. If it's not relevant to *most* tasks, it doesn't belong here.

2. **One concern per `.instructions.md` file.** Don't mix testing rules with API patterns with import conventions. Separate files mean only relevant rules load.

3. **Never duplicate linters.** If ESLint or Ruff already enforces it, the agent doesn't need to be told.

4. **Show, don't tell.** A 3-line code example beats a paragraph of explanation.

5. **Include the "why."** `"Use date-fns because moment.js is deprecated and adds 300KB"` helps the agent reason about edge cases.

6. **Link, don't copy.** Reference your README and docs instead of pasting their content.

7. **Verify commands.** Test that your run/build/test commands actually work before putting them in instructions. Wrong commands waste everyone's time.

8. **Quote YAML colons.** In `.instructions.md` frontmatter, always quote descriptions containing colons: `description: "Use when: doing X"`. Unquoted colons cause silent YAML parse failures.

---

## Troubleshooting

**Instructions aren't being applied?**

  - Right-click in Chat view → **Diagnostics** to see all loaded instruction files
  - Check the **References** section in chat responses to see which files were used
  - Verify `AGENTS.md` is in the workspace root (not a subfolder, unless using nested mode)
  - For `.instructions.md` files, verify `applyTo` glob patterns match your files
  - Check settings: `chat.useAgentsMdFile`, `chat.includeApplyingInstructions`

**Migrating from copilot-instructions.md?**

  1. Copy the content of `.github/copilot-instructions.md` into a new `AGENTS.md` at the workspace root
  2. Delete `.github/copilot-instructions.md`
  3. Verify in Diagnostics that `AGENTS.md` is loading

**Not sure where an instruction came from?**

  - `Ctrl+Shift+P` → **Chat: Configure Instructions** → hover over any instruction to see its source

**Want to generate instructions automatically?**

  - `/init` — generates always-on workspace instructions by analyzing your project
  - `/create-instruction` — generates a targeted `.instructions.md` file from a description

---

## Related VS Code Settings

| Setting | Default | Purpose |
| --- | --- | --- |
| `chat.instructionsFilesLocations` | `{".github/instructions": true, ...}` | Control which folders are searched for `.instructions.md` files |
| `chat.useAgentsMdFile` | `true` | Enable/disable `AGENTS.md` loading |
| `chat.useNestedAgentsMdFiles` | `false` | Enable subfolder `AGENTS.md` hierarchy (experimental) |
| `chat.useClaudeMdFile` | `true` | Enable/disable `CLAUDE.md` loading |
| `chat.includeApplyingInstructions` | `true` | Enable pattern-based `.instructions.md` loading |
| `chat.includeReferencedInstructions` | `true` | Enable instructions referenced via Markdown links |
| `github.copilot.chat.organizationInstructions.enabled` | `false` | Enable org-level instructions |
