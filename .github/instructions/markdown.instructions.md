---
name: "Markdown Formatting"
description: "Use when creating or modifying any Markdown file. Covers nested code block formatting and other Markdown authoring rules."
applyTo: "**/*.md"
---

# Markdown Formatting

This project uses markdownlint. Follow these conventions to avoid lint warnings:

- **FenceAll Codeblocks** — Bare codeblocks with no language specified trigger lint errors. Always specify a language after the opening backticks. Wrap directory trees in code fences labeled as `markdown`.
- **Pad table separator rows** — Always include spaces between pipes and dashes in separator rows `| --- |` not `|---|`.
- **Indent lists** — Always indent lists with 2 spaces, and then an additional 2 spaces for nested levels.

## Nested Code Blocks

**The rule**: When a Markdown example contains triple-backtick fenced code blocks inside it, the outer fence **must** use four backticks. Count nesting levels. The outer fence always needs more backticks than any fence inside it. Two levels = four backticks. Three levels = five backticks.

### Correctly Nested Example.

````markdown
Markdown here

```html
<div>
  <p>
    This html will render correctly because it's wrapped in a fenced code block
    with more backticks.
  </p>
</div>
```

This will render correctly as markdown again. The inner triple backticks are properly nested inside the outer four-backtick fence.
````
