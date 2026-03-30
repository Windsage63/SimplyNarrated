# Example Pipeline Interaction

Complete example of a project pipeline session:

---

**User:** "Start a new project. I want to build a clone of Trello for my team."

---

**Pipeline Agent:**

```markdown
Great! I'll guide you through our Project Pipeline. Here's what will happen:

1. **🏗️ Architecture Phase** — Brainstorm system design
2. **📋 PRD Phase** — Generate specs for each component
3. **🚀 Implementation Ready** — Actionable specs for coding

Let's begin with architecture...
```

---

*[Architect skill runs, produces blueprint]*

---

**Pipeline Agent:**

```markdown
The Architect has identified 5 components:

| # | Component | Priority |
|---|-----------|----------|
| 1 | Auth | P0 |
| 2 | Boards | P0 |
| 3 | Cards | P0 |
| 4 | Teams | P1 |
| 5 | Notifications | P2 |

Should I proceed with generating a PRD for each?
```

**User:** "Yes, proceed."

---

**Pipeline Agent:**

```markdown
Starting PRD for **Auth**. The PRD skill asks:

1. Authentication method?
   A. Email/password
   B. Google OAuth
   C. Both
   D. Enterprise SSO

2. User roles?
   A. Single role
   B. User + Admin
   C. Custom roles
```

**User:** "1C, 2B"

---

*[PRD skill generates and saves `tasks/prd-auth.md`]*

---

**Pipeline Agent:**

```markdown
✅ Auth PRD complete! Saved to `tasks/prd-auth.md`

Progress: 1/5 | Moving to **Boards**...
```

---

*[...repeats for all components...]*

---

**Pipeline Agent:**

```markdown
🎉 **Pipeline Complete!**

Generated:
- `plans/architect_plan.md`
- `tasks/prd-auth.md`
- `tasks/prd-boards.md`
- `tasks/prd-cards.md`
- `tasks/prd-teams.md`
- `tasks/prd-notifications.md`

Ready for implementation! 🚀
```
