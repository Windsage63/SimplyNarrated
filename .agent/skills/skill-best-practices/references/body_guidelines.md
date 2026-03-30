# Body Content Guidelines

Best practices for structuring SKILL.md body content, based on the [Agent Skills best practices](https://agentskills.io/skill-creation/best-practices) and [Anthropic's authoring guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

## Length Constraints

| Metric       | Limit       | Notes                          |
| ------------ | ----------- | ------------------------------ |
| Total lines  | 500         | Hard limit for performance     |
| Total tokens | ~5,000      | Approximate context budget     |
| TOC required | 100+ lines  | Helps agent navigate reference |

## Core Principles

### 1. Add What the Agent Lacks, Omit What It Knows

The agent already knows common programming patterns, language syntax, and general engineering principles. **Only add:**

- Project-specific context and conventions
- Non-obvious workflows and edge cases
- Custom output formats
- Explicit constraints and gotchas
- The particular tools or APIs to use

**Ask about each piece of content:** "Would the agent get this wrong without this instruction?" If no, cut it.

### 2. Match Specificity to Fragility

Not every part of a skill needs the same level of prescriptiveness:

**High freedom** (flexible instructions) — when multiple approaches are valid:

```markdown
## Code review process

1. Check all database queries for SQL injection
2. Verify authentication checks on every endpoint
3. Look for race conditions in concurrent code paths
```

**Medium freedom** (preferred pattern with parameters):

```markdown
## Generate report

Use this template and customize as needed:

| Section | Content |
|---------|---------|
| Summary | Key findings |
| Details | Supporting data |
```

**Low freedom** (exact commands) — when operations are fragile:

````markdown
## Database migration

Run exactly this script:

```bash
python scripts/migrate.py --verify --backup
```

Do not modify the command or add additional flags.
````

### 3. Provide Defaults, Not Menus

Don't present multiple approaches unless necessary:

```markdown
# Bad: Too many choices

You can use pypdf, or pdfplumber, or PyMuPDF, or pdf2image...

# Good: Default with escape hatch

Use pdfplumber for text extraction. For scanned PDFs requiring OCR,
use pdf2image with pytesseract instead.
```

### 4. Examples Over Explanations

```markdown
# Bad: Verbose explanation (150 tokens)

The output should be formatted as a markdown table with three columns.
The first column should contain the component name...

# Good: Concise example (50 tokens)

| Component | Description | Priority |
|-----------|-------------|----------|
| Auth | User authentication | P0 |
```

### 5. Favor Procedures Over Declarations

Teach the agent **how** to approach a class of problems, not **what** to produce for a specific instance:

```markdown
# Bad: Only useful for this exact task

Join the `orders` table to `customers` on `customer_id`, filter where
`region = 'EMEA'`, and sum the `amount` column.

# Good: Reusable method

1. Read the schema from `references/schema.yaml` to find relevant tables
2. Join tables using the `_id` foreign key convention
3. Apply filters from the user's request as WHERE clauses
4. Aggregate numeric columns and format as a markdown table
```

### 6. No Duplication

Information should exist in exactly one place:

- Core instructions → SKILL.md
- Large examples → `references/`
- External schemas → link to source

## Recommended Structure

### Core Sections (Required)

```markdown
## The Job

Brief numbered workflow (5-7 steps max)

## [Main Content]

Skill-specific instructions and patterns

## Stopping Rules

Explicit "do NOT" constraints

## Checklist

Verification steps before completion
```

### Optional Sections

```markdown
## Quick Reference

Summary table for key constraints

## Gotchas

Non-obvious facts that defy reasonable assumptions

## Output Format

Template for skill output
```

## Named Content Patterns

### Gotchas Section

The highest-value content in many skills. Concrete corrections to mistakes the agent will make without being told:

```markdown
## Gotchas

- The `users` table uses soft deletes. Queries must include
  `WHERE deleted_at IS NULL` or results will include deactivated accounts.
- The user ID is `user_id` in the database, `uid` in the auth service,
  and `accountId` in the billing API. All three refer to the same value.
- The `/health` endpoint returns 200 even if the database is down.
  Use `/ready` to check full service health.
```

Keep gotchas in SKILL.md where the agent reads them before encountering the situation.

### Template Pattern

More reliable than describing format in prose:

````markdown
## Report structure

Use this template, adapting sections as needed:

```markdown
# [Analysis Title]

## Executive summary

[One-paragraph overview of key findings]

## Key findings

- Finding 1 with supporting data
- Finding 2 with supporting data

## Recommendations

1. Specific actionable recommendation
```
```

### Checklist Pattern

Helps the agent track progress through multi-step workflows:

```markdown
## Form processing workflow

Progress:
- [ ] Step 1: Analyze the form (run `scripts/analyze_form.py`)
- [ ] Step 2: Create field mapping (edit `fields.json`)
- [ ] Step 3: Validate mapping (run `scripts/validate_fields.py`)
- [ ] Step 4: Fill the form (run `scripts/fill_form.py`)
- [ ] Step 5: Verify output (run `scripts/verify_output.py`)
```

### Validation Loop Pattern

Do the work → validate → fix → repeat until passing:

```markdown
## Editing workflow

1. Make your edits
2. Run validation: `python scripts/validate.py output/`
3. If validation fails:
   - Review the error message
   - Fix the issues
   - Run validation again
4. Only proceed when validation passes
```

### Plan-Validate-Execute Pattern

For batch or destructive operations — create intermediate plan, validate, then execute:

```markdown
## PDF form filling

1. Extract form fields: `python scripts/analyze_form.py input.pdf` → `form_fields.json`
2. Create `field_values.json` mapping each field name to its intended value
3. Validate: `python scripts/validate_fields.py form_fields.json field_values.json`
4. If validation fails, revise and re-validate
5. Fill the form: `python scripts/fill_form.py input.pdf field_values.json output.pdf`
```

### Conditional Workflow Pattern

Guide through decision points:

```markdown
## Document modification workflow

1. Determine the modification type:
   **Creating new content?** → Follow "Creation workflow" below
   **Editing existing content?** → Follow "Editing workflow" below
```

If workflows become large, push them into separate files and tell the agent which file to read based on the task.

### Stopping Rules Pattern

Always include explicit constraints:

```markdown
## Stopping Rules

STOP IMMEDIATELY if you consider:

- [Action that violates scope]
- [Action that belongs to another skill]
- [Action that requires user approval]

This skill's SOLE responsibility is [primary function].
```

## Content Guidelines

### Avoid Time-Sensitive Information

```markdown
# Bad: Will become wrong

If you're doing this before August 2025, use the old API.

# Good: Use "old patterns" section

## Current method

Use the v2 API endpoint: `api.example.com/v2/messages`

## Old patterns

<details>
<summary>Legacy v1 API (deprecated 2025-08)</summary>
The v1 API used: `api.example.com/v1/messages`
</details>
```

### Use Consistent Terminology

Choose one term and use it throughout:

- Always "API endpoint" (not "URL", "API route", "path")
- Always "field" (not "box", "element", "control")
- Always "extract" (not "pull", "get", "retrieve")

### Use Forward Slashes in Paths

Always use forward slashes, even on Windows:

- Good: `scripts/helper.py`, `reference/guide.md`
- Bad: `scripts\helper.py`, `reference\guide.md`

## Development Workflow

### Evaluation-Driven Development

1. **Run tasks without a skill** — document specific failures
2. **Create evaluations** — build ~20 test scenarios (10 should-trigger, 10 should-not-trigger)
3. **Establish baseline** — measure agent performance without the skill
4. **Write minimal instructions** — address only the gaps
5. **Iterate** — execute evaluations, compare against baseline, refine

### Iterative Development with Claude

Work with **Claude A** (the expert) to create skills that **Claude B** (fresh instance) uses:

1. Complete a task without a skill — note what context you provided
2. Identify the reusable pattern
3. Ask Claude A to create a skill from that pattern
4. Review for conciseness — "Remove the explanation about X, Claude already knows that"
5. Improve information architecture — organize into reference files
6. Test with Claude B on similar tasks
7. Iterate based on Claude B's behavior — bring insights back to Claude A

### Observe How Claude Navigates Skills

Watch for:

- **Unexpected exploration paths** — structure may not be intuitive
- **Missed connections** — links may need to be more explicit
- **Overreliance on certain sections** — content may belong in SKILL.md
- **Ignored content** — files may be unnecessary or poorly signaled

## What to Avoid

| Anti-Pattern                | Why It's Bad                                     |
| --------------------------- | ------------------------------------------------ |
| Explaining basic concepts   | Wastes tokens on what the agent knows            |
| Repeating information       | Inflates size, risks inconsistency               |
| Vague instructions          | "Make it good" vs "Follow this template"         |
| Too many options            | Overwhelms; provide defaults                     |
| Nested conditionals         | Hard to follow, error-prone                      |
| Wall of text                | No structure, hard to navigate                   |
| Windows-style paths         | Breaks on Unix; use forward slashes              |
| Time-sensitive references   | Will become wrong; use "old patterns" sections   |
| Magic numbers               | Undocumented constants confuse the agent         |
