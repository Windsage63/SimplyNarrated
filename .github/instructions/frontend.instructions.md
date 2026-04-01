---
name: "Frontend JavaScript"
description: "Use when creating or modifying frontend JavaScript or HTML. Covers SPA architecture, view lifecycle, state management, and DOM safety."
applyTo: "static/**"
---

# Frontend Conventions

## Structure

```markdown
static/
├── index.html                  # Single HTML shell: nav, view container, Tailwind config, styles
├── js/
│   ├── app.js                  # Global state, API client, SPA router (showView), and utilities
│   └── views/
│       ├── landing.js          # Hero section and feature cards
│       ├── upload.js           # File drop zone, voice picker, quality/filter options
│       ├── progress.js         # Real-time job polling with activity log and progress bar
│       ├── dashboard.js        # Library grid with search, sort, import/export
│       └── player.js           # Audio player, chapter sidebar, text edit modal, bookmarks
├── img/                        # Static images
└── vendor/                     # Bundled offline assets (Tailwind, fonts, icons)
```

## Architecture

- **No build step** — files are served directly by FastAPI's `StaticFiles` mount. Edit and reload
- **No framework** — vanilla JS with a global `state` object, centralized `api` client, and manual DOM rendering
- **Tailwind CSS** — configured inline in `index.html` via local JIT compiler (`static/vendor/tailwind/tailwindcss.js`). Custom colors: `primary`, `dark-900` through `dark-600`
- All scripts are loaded via `<script>` tags in `index.html` — view files share the global scope

## View Lifecycle

Each view has two functions in `static/js/views/{name}.js`:

1. `renderXxxView()` — returns an HTML string (no side effects)
2. `initXxxView()` — attaches event handlers, fetches data, starts polling

`showView()` in `app.js` orchestrates: sets `state.currentView`, updates nav active state, calls `render`, injects into `#view-container`, then calls `init`. The player view also calls `teardownPlayerView()` on exit to clean up audio resources.

## State & API

- Global `state` object holds current view, selected book/job, voice, audio settings, and library list
- `api` object in `app.js` wraps all `fetch()` calls with async methods — always use `api.xxx()` instead of raw `fetch`
- View-local state (e.g., `dashboardState`, `playerState`) is a module-level object in the view file

## DOM Safety

- Use `textContent` (not `innerHTML`) when inserting user-provided text (titles, authors, chapter text)
- `innerHTML` is acceptable only for trusted template strings built from code-controlled values
- Inline `onclick` handlers reference global functions — keep handler functions at module scope
