---
name: create-instructions
description: "Study a repo and create the AGENTS.md and .instructions.md files that best suit it. Analyzes codebase structure, conventions, and submodule boundaries to decide what goes in always-on AGENTS.md vs targeted .instructions.md files. Triggers on: create instructions, create AGENTS.md, update AGENTS.md, check instructions, instruction files, study repo."
---

# Create Instructions

Study a repository and produce the right mix of instruction files for it: a root `AGENTS.md` for universal rules, subfolder `AGENTS.md` files for monorepo overrides, and `.instructions.md` files for targeted file-specific or task-specific guidance. Decide what goes where based on the actual codebase structure.

## The Instruction File System

Two categories of files. Understand both before deciding what to create.

### Always-on: `AGENTS.md`

Loads into every agent interaction, automatically. Plain Markdown, no frontmatter.

- **Root `AGENTS.md`** — Universal project rules. The "constitution" of the codebase.
- **Subfolder `AGENTS.md`** — Overrides for monorepo submodules. Closest file to the code being edited wins. Requires VS Code setting `chat.useNestedAgentsMdFiles`.

### Targeted: `*.instructions.md`

Loads only when relevant. Lives in `.github/instructions/`. Uses YAML frontmatter for discovery.

Three activation modes:

| Mode          | Frontmatter                                  | Loads When                            |
| ------------- | -------------------------------------------- | ------------------------------------- |
| **Explicit**  | `applyTo: "src/api/**"`                      | Agent creates/modifies matching files |
| **On-demand** | `description: "Use when writing migrations"` | Agent detects task relevance          |
| **Both**      | `applyTo` + `description`                    | Either trigger fires                  |

**Critical:** `applyTo` fires when the agent **creates or modifies** matching files, not when reading them.

### What NOT to create

- **Never both `AGENTS.md` and `copilot-instructions.md`** — they conflict. If `copilot-instructions.md` exists, migrate it to `AGENTS.md` and delete the old file.
- **Never create a `CLAUDE.md`** if one already exists — VS Code loads it alongside `AGENTS.md`. Don't duplicate.

## The Job

1. **Deep-scan** the repo — structure, stack, conventions, commands, submodule boundaries
2. **Decide** the file plan — which files to create and what goes in each
3. **Draft** each file using the quality principles
4. **Validate** accuracy, then present the plan to the user
5. **Save** and confirm

## Step 1: Deep-Scan the Project

Use subagents or parallel tool calls. **Do not ask the user what you can learn by reading the codebase.**

### Discovery Checklist

1. **Tech stack** — `package.json`, `requirements.txt`, `*.csproj`, `go.mod`, `Cargo.toml`, `pyproject.toml`. Note languages, frameworks, key dependencies
2. **Directory structure** — Map the tree. Identify source dirs, test dirs, config, build outputs, data dirs
3. **Entry points** — How to run, test, build, install. Check `Makefile`, `package.json` scripts, `*.bat`/`*.sh`, `docker-compose.yml`
4. **Architecture** — Read main entry points to understand module organization, routing, and application structure
5. **Data layer** — Database, ORM, file-based storage, external APIs
6. **Test setup** — Config files (`pytest.ini`, `jest.config`, etc.), test commands, markers, fixtures
7. **Conventions** — Sample 3-5 source files for patterns: naming, error handling, imports, module structure, file headers
8. **Linter/formatter config** — `.eslintrc`, `ruff.toml`, `.prettierrc`, `pyproject.toml [tool.*]`. Note what's already enforced (don't repeat these in instruction files)
9. **Existing docs** — `README.md`, `CONTRIBUTING.md`, `docs/**/*.md`. Note what each covers so you link instead of duplicate
10. **Existing instruction files** — Check for `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.github/instructions/`. If any exist, read them and plan updates, not replacements
11. **Submodule boundaries** — Identify distinct areas with different tech stacks, conventions, or concerns (e.g., `frontend/` vs `backend/`, `image-manager/` vs `training-hub/`)

### Optional Discovery

12. **CI/CD** — `.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`
13. **Environment** — Embedded runtimes, vendored dependencies, Docker, special runtime requirements
14. **API surface** — Routing patterns and key endpoints (web apps)

## Step 2: Decide the File Plan

This is the critical step. Based on what you found, decide **what files to create and what content goes where**.

### Decision Framework

```markdown
For each rule or convention discovered, ask:

Does it apply to EVERY task in the project?
├── Yes → Root AGENTS.md
│
└── No → Is this a monorepo with distinct submodules?
├── Yes → Does it apply to all tasks within one submodule?
│ ├── Yes → Subfolder AGENTS.md
│ └── No → .instructions.md (applyTo or description)
│
└── No → Does it apply to specific file types or folders?
├── Yes → .instructions.md with applyTo
└── No → .instructions.md with description (on-demand)
```

### When to Use Each File

**Root `AGENTS.md`** — Use for:

- Project overview (always)
- Verified run/test/build commands (always)
- Architecture overview (multi-module projects)
- Conventions that apply uniformly across the entire codebase
- Environment quirks (embedded runtimes, vendored deps)

**Subfolder `AGENTS.md`** — Use when:

- The repo has distinct submodules with different tech stacks or contradictory conventions
- A subfolder has its own run/test/build commands
- Example: `frontend/AGENTS.md` with React rules, `backend/AGENTS.md` with API rules

**`.instructions.md` with `applyTo`** — Use when:

- Rules apply to a specific file glob (e.g., `tests/**`, `src/api/**`, `static/js/**`)
- The content would waste context budget if loaded for every interaction
- Different folders within the same tech stack have different patterns

**`.instructions.md` with `description` only** — Use when:

- Rules apply to a task type regardless of which files are open (e.g., "writing migrations", "database schema changes")
- No clean file glob exists for the concern

### Monolithic vs Split: How to Decide

A single `AGENTS.md` with everything in it is **correct** when:

- One tech stack across the repo
- Conventions apply uniformly everywhere
- The file stays under ~200 lines
- No contradictory rules between areas (e.g., frontend vs backend)

Split into `AGENTS.md` + `.instructions.md` files when:

- Different areas have different or contradictory conventions
- The root file would exceed ~200 lines
- Clean `applyTo` boundaries exist between concern areas
- File-specific rules would waste context on unrelated tasks

### File Plan Template

Present this to the user before drafting:

```markdown
## Proposed Instruction Files

### AGENTS.md (root)

- Project overview
- Commands (run, test, build)
- Architecture tree
- [list specific conventions that are universal]

### .github/instructions/testing.instructions.md

- applyTo: "tests/\*\*"
- [list test-specific conventions]

### .github/instructions/frontend.instructions.md

- applyTo: "static/js/\*\*"
- [list frontend-specific conventions]

### No file needed for:

- [things already in README, linter config, etc.]
```

## Step 3: Draft the Files

Read [references/section_guide.md](references/section_guide.md) for section-by-section templates and examples.

### Quality Principles (apply to ALL file types)

1. **Earn the context budget** — Always-on files load every interaction. Targeted files load less often but still cost tokens. Every line must justify its inclusion
2. **Concise and actionable** — Each instruction directly guides agent behavior. No aspirational statements
3. **Link, don't embed** — Reference existing docs. `See [docs/API-Reference.md](docs/API-Reference.md)` beats copying the content
4. **Non-obvious over obvious** — Focus on what the agent would get wrong. Skip standard language conventions and known framework patterns
5. **Show, don't tell** — A 3-line code example beats a paragraph of prose
6. **Skip linter-enforced rules** — If a formatter or linter catches it, don't mention it
7. **Include the "why"** — Rules with rationale help agents reason about edge cases
8. **Verified commands only** — Run commands before including them. Invalid commands waste everyone's time

### AGENTS.md Content Rules

No YAML frontmatter. Plain Markdown.

| Section          | Include When                                                    |
| ---------------- | --------------------------------------------------------------- |
| Project Overview | Always — 2-3 sentences, what it does, key tech                  |
| Commands         | Always — run, test, build, install. Verified and copy-pasteable |
| Environment      | Non-standard runtime (embedded Python, Docker, vendored deps)   |
| Architecture     | Multi-module projects with non-obvious structure                |
| Data Layer       | When storage patterns aren't obvious from code                  |
| Key Conventions  | When the project has patterns that deviate from defaults        |
| Testing          | When test setup has non-obvious requirements or markers         |

### .instructions.md Content Rules

YAML frontmatter is required. Keep these files tightly focused — one concern per file.

**Frontmatter format:**

```yaml
---
name: "Human-readable name"
description: "Use when [specific task]. Covers [specific topics]."
applyTo: "path/glob/**"
---
```

**Frontmatter rules:**

- `description` — Front-load the use case. First sentence should say when to apply it. Always quote strings containing colons
- `applyTo` — Use the narrowest glob that captures the target files. Multiple files need separate `.instructions.md` files (no array syntax for `applyTo`)
- `name` — Optional but helpful for diagnostics display

**Body rules:**

- Lead with the most important conventions — agents weight earlier content higher
- Use bullet points, not long paragraphs
- Include code examples for non-obvious patterns
- Keep under 50 lines of content per file. If it's longer, split into multiple files
- Don't repeat rules from `AGENTS.md` — these files complement the root, not duplicate it

## Step 4: Validate

### For each AGENTS.md file:

- [ ] No YAML frontmatter
- [ ] Correct location (root for global, subfolder for overrides)
- [ ] Commands verified in the actual environment
- [ ] No duplication of README, CONTRIBUTING, or other docs
- [ ] No linter-enforced rules repeated
- [ ] No obvious language/framework conventions stated
- [ ] Links to existing docs where appropriate
- [ ] Every line earns its context budget
- [ ] File paths and module descriptions match the actual codebase

### For each .instructions.md file:

- [ ] Valid YAML frontmatter with `description` (always) and `applyTo` (when target files exist)
- [ ] Description quoted if it contains colons
- [ ] `applyTo` glob is as narrow as possible
- [ ] Content doesn't repeat rules from `AGENTS.md`
- [ ] Tightly focused — one concern per file
- [ ] Placed in `.github/instructions/` directory

### Cross-file checks:

- [ ] Not creating both `AGENTS.md` and `copilot-instructions.md`
- [ ] No content duplicated across files
- [ ] Universal rules are in `AGENTS.md`, not in `.instructions.md` files
- [ ] File-specific rules are in `.instructions.md`, not bloating `AGENTS.md`

## Step 5: Save and Confirm

After saving all files:

1. List every file created/updated with a one-line summary
2. If `copilot-instructions.md` existed and was migrated, confirm the old file was removed
3. Note any `.instructions.md` files that could be added later as the project grows
4. Remind the user to enable `chat.useNestedAgentsMdFiles` if subfolder `AGENTS.md` files were created
5. Suggest verifying via Chat > right-click > **Diagnostics** to confirm files are loading

## Gotchas

- **Always-on means always-on** — Every token in `AGENTS.md` loads for every interaction, even trivial questions. Keep it lean
- **Subfolder AGENTS.md requires a setting** — `chat.useNestedAgentsMdFiles` must be enabled or only root loads
- **`applyTo` triggers on create/modify only** — Not on reads. An `.instructions.md` targeting `tests/**` won't load when the agent is just reading tests for context
- **YAML colon trap** — Unquoted colons in `.instructions.md` `description` cause silent parse failures. Always quote: `description: "Use when: doing X"`
- **Test commands in the actual environment** — Embedded Pythons, Docker containers, and vendored dependencies break standard commands. Run them first
- **Don't duplicate CLAUDE.md** — VS Code loads it too. If it exists, check what it covers and avoid overlap
- **Don't duplicate README** — The agent can read it when needed. Instructions contain what the agent needs to know _without_ reading the README
- **One `applyTo` per file** — You can't specify multiple globs. Create separate `.instructions.md` files for separate concerns

## Stopping Rules

STOP and reconsider if you're about to:

- Create both `copilot-instructions.md` and `AGENTS.md` — migrate to `AGENTS.md`
- Put file-specific rules in `AGENTS.md` — use `.instructions.md` with `applyTo` instead
- Put universal rules in `.instructions.md` files — they belong in `AGENTS.md`
- Duplicate content already in README, CONTRIBUTING, or docs
- Include rules already enforced by linters or formatters
- Create a skill — skills are for multi-step workflows with bundled assets, not static rules
