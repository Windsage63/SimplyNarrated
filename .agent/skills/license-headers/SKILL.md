---
name: license-headers
description: "Helps to write proper Apache 2.0 license headers into the project files. Triggers on: apply license headers, add license, license header, check license, Apache 2.0 license."
---

# License Headers Skill

Automate the process of adding Apache 2.0 license headers to project files to ensure consistency and compliance.

## The Job

1. Identify files in the project that are missing the Apache 2.0 license header.
2. Apply the header at the top of the file using the correct comment syntax for the file type.
3. Ensure placeholders like `{explains the purpose of the file}` and copyright years are correctly populated.

## License Header Template

Use the following template for the license header:

```javascript
/**
 * @fileoverview {explains the purpose of the file}
 * @author {author_name}
 * @license Apache-2.0
 * @copyright {copyright_years} {author_name}
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
```

## Implementation Rules

### 1. Identify File Type

- **JavaScript (.js)**: Use the `/** ... */` block comment syntax shown above.
- **CSS (.css)**: Use the `/** ... */` block comment syntax shown above.
- **HTML (.html)**: Wrap the entire block in HTML comment tags: `<!-- ... -->`.

### 2. Header Placement

- The header MUST be the very first thing in the file.
- Add an empty line after the header block.

### 3. Populate Placeholders

- **@fileoverview**: Briefly explain what the file does.
- **@author**:
  - Use the name supplied by the user in the current request or chat history.
  - If not supplied, infer from other project files (e.g., check `js/app.js` or `package.json`).
  - If no author is found or inferred, ask the user.
- **@copyright**:
  - **Year Range**: Detect the file's creation year (e.g., via `git log --follow --format=%ad --date=format:%Y [file]` or file metadata).
  - If the creation year is the same as the current year, use a single year (e.g., `2026`).
  - If the creation year is earlier than the current year, use a range (e.g., `2025-2026`).
  - **Name**: Use the same author name identified for the `@author` tag.

## Stopping Rules

- Do NOT add a license header to files that already have one.
- Do NOT modify the `LICENSE` file or any files in `.git/`, `node_modules/`, or other dependency folders.
- Do NOT add headers to `.json`, `.md`, or image files unless explicitly requested.

## Checklist

- [ ] File type identified and correct comment syntax used.
- [ ] Header placed at the very top of the file.
- [ ] Placeholders populated with relevant information.
- [ ] Empty line added after the header.
- [ ] Original file content preserved below the header.
