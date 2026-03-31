# Progressive Disclosure

How to organize skill content across multiple files for efficient context loading. Based on the [Agent Skills specification](https://agentskills.io/specification#progressive-disclosure) and [Anthropic's authoring guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

---

## The Three-Level System

Agents load skill content progressively:

| Level | Content                | When Loaded        | Budget             |
| ----- | ---------------------- | ------------------ | ------------------ |
| 1     | `name` + `description` | Always (startup)   | ~100 tokens        |
| 2     | SKILL.md body          | On skill trigger   | < 5,000 tokens     |
| 3     | Reference files        | On explicit need   | Unlimited          |

## When to Extract to Reference Files

### Extract When

  - **Large examples** (50+ lines of code/output)
  - **Complete templates** (full file structures)
  - **Detailed specifications** (API schemas, format specs)
  - **Domain-specific content** (reference docs per domain area)
  - **Variant-specific content** (language-specific instructions)
  - **Historical context** (changelog, migration guides)

### Keep Inline When

  - **Brief examples** (under 20 lines)
  - **Core workflow steps** (always needed)
  - **Quick reference tables** (frequently consulted)
  - **Gotchas** (non-obvious facts the agent needs before encountering the situation)
  - **Stopping rules and checklists** (critical constraints)

## Key Design Principle: Tell the Agent When to Load Each File

Don't just link to reference files — specify the **condition** that triggers loading:

```markdown
# Good — conditional triggers

Read `references/api-errors.md` if the API returns a non-200 status code.
For scanned PDFs requiring OCR, see `references/ocr-setup.md`.

# Bad — vague pointers

See references/ for details.
For more information, check the reference files.
```

This lets the agent load context on demand rather than up front, which is how progressive disclosure is designed to work.

## File Organization

Follow the canonical file organization structure defined in the parent SKILL.md.

### Naming Conventions

| Type      | Pattern                 | Example                  |
| --------- | ----------------------- | ------------------------ |
| Examples  | `example_[what].md`     | `example_blueprint.md`   |
| Templates | `template_[what].md`    | `template_prd.md`        |
| Specs     | `spec_[topic].md`       | `spec_api_format.md`     |
| Guides    | `guide_[topic].md`      | `guide_migration.md`     |
| Domain    | `[domain].md`           | `finance.md`, `sales.md` |

Name files descriptively — `form_validation_rules.md`, not `doc2.md`.

## Disclosure Patterns

### Pattern 1: High-Level Guide with References

The most common pattern. SKILL.md provides quick start and navigation:

````markdown
# PDF Processing

## Quick start

Extract text with pdfplumber:

```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## Advanced features

**Form filling**: See [FORMS.md](FORMS.md) for complete guide
**API reference**: See [REFERENCE.md](REFERENCE.md) for all methods
**Examples**: See [EXAMPLES.md](EXAMPLES.md) for common patterns
````

The agent loads FORMS.md, REFERENCE.md, or EXAMPLES.md only when needed.

### Pattern 2: Domain-Specific Organization

For skills with multiple domains, organize by domain to avoid loading irrelevant context:

```markdown
bigquery-skill/
├── SKILL.md (overview and navigation)
└── references/
    ├── finance.md (revenue, billing metrics)
    ├── sales.md (opportunities, pipeline)
    ├── product.md (API usage, features)
    └── marketing.md (campaigns, attribution)
```

```markdown
# BigQuery Data Analysis

## Available datasets

**Finance**: Revenue, ARR, billing → See [references/finance.md](references/finance.md)
**Sales**: Opportunities, pipeline → See [references/sales.md](references/sales.md)
**Product**: API usage, features → See [references/product.md](references/product.md)
**Marketing**: Campaigns, attribution → See [references/marketing.md](references/marketing.md)
```

When a user asks about revenue, the agent only reads `references/finance.md`.

### Pattern 3: Conditional Details

Show basic content inline, link to advanced content conditionally:

```markdown
# DOCX Processing

## Creating documents

Use docx-js for new documents. See [DOCX-JS.md](DOCX-JS.md).

## Editing documents

For simple edits, modify the XML directly.

**For tracked changes**: See [REDLINING.md](REDLINING.md)
**For OOXML details**: See [OOXML.md](OOXML.md)
```

The agent reads REDLINING.md or OOXML.md only when the user needs those features.

## Linking From SKILL.md

### Standard Pattern

```markdown
See [reference.md](reference.md) for the complete API reference.
```

### With Condition

```markdown
Read [references/api-errors.md](references/api-errors.md) if the API returns a non-200 status code.
```

### With Context

```markdown
## Complete Example

See [references/example_blueprint.md](references/example_blueprint.md) for a realistic completed architectural blueprint (TaskFlow example).
```

## Critical Rule: No Deep Nesting

Reference files must be **one level deep** from SKILL.md.

### Correct

```markdown
SKILL.md → references/example.md
```

### Incorrect

```markdown
SKILL.md → references/example.md → references/sub/detail.md
```

**Why:** Agents may only partially read deeply nested references (using `head -100` previews), leading to incomplete context.

## Reference File Structure

Each reference file should be self-contained:

```markdown
# [Title]

Brief description of what this file contains.

## [Section 1]

Content...

## [Section 2]

Content...
```

**Do NOT include:**

  - Frontmatter (not needed for reference files)
  - Links back to SKILL.md (circular)
  - Links to other reference files (creates nesting)

## Scripts: Execute vs. Read

Make clear whether the agent should execute or read a script:

```markdown
# Execute (most common, more reliable and efficient)

Run `analyze_form.py` to extract fields

# Read as reference (for understanding complex logic)

See `analyze_form.py` for the extraction algorithm
```

Scripts that are executed don't consume context tokens — only their output does. This makes bundled scripts more efficient than generating code each time.
