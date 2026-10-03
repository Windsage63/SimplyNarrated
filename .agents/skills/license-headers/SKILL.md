---
name: license-headers
description: "Writes proper Apache 2.0 license headers into supported JavaScript, CSS, and HTML project files. Triggers on: apply license headers, add license, license header, check license, Apache 2.0 license."
---

# License Headers Skill

Automate the process of adding Apache 2.0 license headers to project files to ensure consistency and compliance.

## The Job

1. Identify first-party source files in the requested scope. Include application code, startup scripts, configuration scripts, tests, and test helpers.
2. Apply the header at the top of the file using the correct comment syntax for the file type.
3. Ensure placeholders like `{explains the purpose of the file}` and copyright years are correctly populated.

## License Header Template

Use the following template for the license header:

```javascript
/**
 * @fileoverview {explains the purpose of the file}
 * @license Apache-2.0
 * @copyright {copyright_years} {author_name}
 */
```

```Python
"""
@fileoverview {explains the purpose of the file}
@license Apache-2.0
@copyright {copyright_years} {author_name}
"""
```

## Implementation Rules

### 1. Identify File Type

  - **JavaScript (.js)**: Use the `/** ... */` block comment syntax shown above.
  - **CSS (.css)**: Use the `/** ... */` block comment syntax shown above.
  - **TypeScript (.ts)**: Use the `/** ... */` block comment syntax shown above.
  - **Shell Scripts (.sh)**: Use the `# ...` line comment syntax, prefixing each line with `#`.
  - **Python (.py)**: Use the `""" ... """` block comment syntax shown above.
  - **HTML (.html)**: Wrap the entire block in HTML comment tags: `<!-- ... -->`.

### 2. Header Placement

  - The header MUST be the very first thing in the file.
  - Add an empty line after the header block.

### 3. Populate Placeholders

  - **@fileoverview**: Briefly explain what the file does.
  - **@license**: Always use `Apache-2.0`.
   - **@copyright**:
     - **Year Range**: Detect the file's creation year (e.g., via `git log --follow --format=%ad --date=format:%Y [file]` or file metadata).
     - If the creation year is the same as the current year, use a single year (e.g., `2026`).
     - If the creation year is earlier than the current year, use a range (e.g., `2025-2026`).
     - **author_name**: Use the same author name identified for the `@author` tag.
       - Use the name supplied by the user in the current request or chat history.
       - If not supplied, infer from other project files (e.g., check `js/app.js` or `package.json`).
       - If no author is found or inferred, ask the user.

## Boundaries

  - Keep the complete root `LICENSE` file intact.
  - Preserve bundled/dependency licenses and notices, including `*/vendor`. Do not standardize third-party files.
  - Exclude `.git`, `node_modules`, generated artifacts, and unrelated skills.
  - Do not add headers to JSON, Markdown, images, or other unsupported formats unless explicitly requested.
  - Make edits through the repository-approved editing mechanism. A request to edit does not bypass filesystem permissions.

## Checklist

  - [ ] File type identified and correct comment syntax used.
  - [ ] Header placed at the very top of the file.
  - [ ] Placeholders populated with relevant information.
  - [ ] Empty line added after the header.
  - [ ] Original file content preserved below the header.
