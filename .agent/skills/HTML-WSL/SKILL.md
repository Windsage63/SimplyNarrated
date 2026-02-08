---
name: html-wsl
description: "Maps WSL Linux file paths to Windows browser URLs for previewing HTML files. Triggers on: open in browser, preview html, wsl file path, browser preview."
---

# Universal HTML-WSL Skill

## Context

Standard Linux file URIs (`file:///home/...`) do not resolve when passed to Windows-native browsers. To bridge this, you must use the `wsl.localhost` network share.

**Critical Compatibility:**

- **Chrome** accepts varying slash counts, but defaults to displaying 2 slashes (`file://wsl.localhost/...`).
- **Firefox** defaults to displaying 5 slashes (`file://///`), but also appears to work with 2 slashes.
- Using 5 slashes ensures universal compatibility across all browser engines.

## Instructions

To construct a valid browser URL for any file in your current environment, follow these steps:

1. **Identify the Distribution**: Determine the name of your WSL distribution (e.g., `Ubuntu-24.04`).
2. **Get Absolute Path**: Obtain the absolute path of the file within the Linux filesystem (e.g., `/home/user/project/index.html`).
3. **Construct the URI**: Combine them using the following template:
    `file://///wsl.localhost/<DISTRO><ABSOLUTE_PATH>`

## Example Formula

| Variable | Value |
| :--- | :--- |
| **Distro** | `Ubuntu-24.04` |
| **Path** | `/home/wind/projects/Infographic/index.html` |
| **Result** | `file://///wsl.localhost/Ubuntu-24.04/home/wind/projects/Infographic/index.html` |

## Expected Output

Whenever calling browser tools or providing links to the user in a WSL context, always use the 5-slash `wsl.localhost` transformation logic to ensure the page opens successfully regardless of the user's default browser or specific project path.
