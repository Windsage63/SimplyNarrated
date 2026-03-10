# Example Architectural Blueprint

Here's a realistic completed blueprint:

```markdown
# TaskFlow - Architectural Blueprint

## 1. Executive Summary

TaskFlow is a team task management application that replaces our current spreadsheet-based workflow. The architecture prioritizes simplicity and fast iteration, using a monolithic Next.js application with PostgreSQL for data persistence.

## 2. Technical Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Next.js 14 (App Router) | Full-stack React, SSR for SEO |
| Backend | Next.js API Routes | Unified codebase, simpler deployment |
| Database | PostgreSQL | Relational data, proven reliability |
| Auth | NextAuth.js | Built-in OAuth, session management |
| Hosting | Vercel | Zero-config Next.js deployment |

## 3. Core Architectural Decisions

### Decision 1: Monolithic over Microservices
- **Choice:** Single Next.js application
- **Rationale:** Team size is small (2-3 devs), complexity not warranted
- **Trade-offs:** Harder to scale individual components later

### Decision 2: Server Components First
- **Choice:** Default to React Server Components, client only when needed
- **Rationale:** Better performance, simpler data fetching
- **Trade-offs:** Learning curve for team used to client-side React

## 4. Component Breakdown

| Component | Description | Priority |
|-----------|-------------|----------|
| Auth | User login/signup with Google OAuth | P0 |
| Tasks | CRUD operations for tasks | P0 |
| Boards | Kanban-style board view | P0 |
| Teams | Multi-user workspaces | P1 |
| Notifications | Email + in-app alerts | P2 |

## 5. System Design

The application follows a standard three-tier architecture:

1. **Presentation Layer:** Next.js React components
2. **Business Logic:** Next.js API routes + server actions
3. **Data Layer:** Prisma ORM → PostgreSQL

### Data Flow
1. User authenticates via Google OAuth
2. Session stored in encrypted cookie
3. User creates/modifies tasks via server actions
4. Changes persisted to PostgreSQL via Prisma
5. Real-time updates via polling (v1) or WebSocket (v2)

## 6. Requirements & Acceptance Criteria

- [ ] FR-1: Users can sign in with Google account
- [ ] FR-2: Users can create, edit, and delete tasks
- [ ] FR-3: Tasks can be organized into boards
- [ ] FR-4: Tasks can be dragged between columns
- [ ] NFR-1: Page load under 2 seconds
- [ ] NFR-2: Support 100 concurrent users

## 7. Planning Agent Handoff

> [!IMPORTANT]
> Start with Auth. Nothing else works without it.

### Primary Goal for Planner
Implement Google OAuth authentication with session persistence.

### Suggested Implementation Order
1. **Auth** — Foundation for all user-specific features
2. **Tasks (CRUD)** — Core value proposition
3. **Boards** — Organizational structure for tasks
4. **Teams** — Multi-user collaboration
5. **Notifications** — Nice-to-have, defer if needed

### Risks to Watch
- **OAuth callback URL:** Must be configured correctly in Google Console
- **Database migrations:** Use Prisma migrate, test on staging first
- **Drag-and-drop:** Complex state management, consider dnd-kit library

### Reference Files
- `prisma/schema.prisma` — Database schema
- `app/api/auth/[...nextauth]/route.ts` — Auth configuration
- `components/TaskCard.tsx` — Reusable task component

## 8. Open Questions

- [ ] Should we support multiple OAuth providers (GitHub, Microsoft)?
- [ ] What is the maximum number of tasks per board?
- [ ] Do we need task due dates in v1?
```
