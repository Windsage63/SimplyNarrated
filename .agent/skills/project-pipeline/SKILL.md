---
name: project-pipeline
description: "Orchestrates the complete lifecycle of a new software project. Use this skill to initiate a new project from a vague idea, guiding it through architectural brainstorming, component definition, and detailed PRD generation. Triggers on: start a new project, kickoff project, project pipeline, new product, build me a, I have an idea for."
---

# Project Pipeline Skill

Orchestrate the complete journey from vague idea to implementation-ready specifications.

## Table of Contents

1. [The Job](#-the-job)
2. [When to Use](#-when-to-use)
3. [Phase 1: Introduction](#phase-1-what-to-do)
4. [Phase 2: Blueprint Review](#phase-2-what-to-do)
5. [Phase 3: PRD Generation Sprint](#-phase-3-prd-generation-sprint)
6. [Phase 4: Handoff](#phase-4-what-to-do)
7. [Output Artifacts](#-output-artifacts)
8. [Key Principles](#-key-principles)
9. [Complete Example](#-complete-example-interaction)
10. [Stopping Rules](#-stopping-rules)
11. [Completion Checklist](#-completion-checklist)

---

## ⚡ The Job

1. Receive user's initial project idea
2. Explain the pipeline process (Architecture → PRDs → Implementation)
3. Trigger the `architect` skill to create system blueprint
4. Review blueprint with user and confirm component list
5. Trigger the `prd` skill for each component (user answers questions)
6. Present complete PRD collection for implementation handoff

**Important:** Do NOT write application code. Only orchestrate planning skills.

---

## 🎯 When to Use

### ✅ Use This Skill For

- **New projects from scratch** — "Build me a task management app"
- **Major product expansions** — "We need to add a whole reporting module"
- **Idea → Plan conversion** — "I have an idea for a SaaS product"

### ❌ Do NOT Use For

- Small bug fixes or single features → Use `prd` skill directly
- Technical deep-dives on existing code → Use `architect` skill directly
- Implementation questions → Use coding skills

---

### Phase 1: What to Do

1. Receive the user's initial idea (can be as vague as "I want an app for X")
2. Explain the full pipeline process
3. Hand off to the `architect` skill

### Phase 1: What to Say

```markdown
Great! I'll guide you through our Project Pipeline. Here's what will happen:

1. **🏗️ Architecture Phase** — I'll use the `architect` skill to brainstorm the system design with you. This produces a technical blueprint.

2. **📋 PRD Phase** — For each major component we identify, I'll generate a detailed Product Requirements Document. You'll answer questions for each one.

3. **🚀 Implementation Ready** — You'll have a set of actionable specs that coding agents can execute.

Let's begin with architecture. Handing off to the Architect skill now...
```

### Trigger Instructions for Architect

Tell the Architect to:

- Focus on identifying major system **Components**
- List components clearly in the "Component Breakdown" section
- Include priority levels (P0/P1/P2) for each component

---

### Phase 2: What to Do

1. Present `plans/architect_plan.md` summary to user
2. List all identified components with priorities
3. Ask for confirmation before proceeding
4. Record any modifications

### Phase 2: What to Say

```markdown
The Architect has completed the blueprint. Here's what was identified:

**Components:**
| # | Component | Description | Priority |
|---|-----------|-------------|----------|
| 1 | Auth | User authentication system | P0 |
| 2 | Tasks | Core task CRUD operations | P0 |
| 3 | Boards | Kanban board interface | P0 |
| 4 | Teams | Multi-user workspaces | P1 |
| 5 | Notifications | Email and in-app alerts | P2 |

**Next step:** I'll generate a PRD for each component. You'll answer 3-5 clarifying questions per component.

Should I proceed with all 5 components, or would you like to modify this list?
```

### Handling Modifications

If user wants changes:

```markdown
Got it. I'll update the component list:
- ❌ Removed: [component]
- ➕ Added: [component]
- 📝 Modified: [component] — [change]

Updated list: [new list]. Proceeding with PRD generation.
```

---

## 📋 Phase 3: PRD Generation Sprint

For **each component** in the confirmed list:

### Step 3.1: Trigger PRD Skill

Provide context from the Architect Plan:

```markdown
Starting PRD generation for **[Component Name]**.

Context from Architect Plan:
- Purpose: [from blueprint]
- Priority: [P0/P1/P2]
- Dependencies: [related components]

Handing off to the PRD skill...
```

### Step 3.2: Facilitate Q&A

The PRD skill will ask clarifying questions in A/B/C/D format.

**Critical:** The USER answers these questions. Do NOT answer on their behalf.

```markdown
The PRD skill has questions for you:

1. What is the primary goal of the Auth component?
   A. Simple email/password login
   B. Social OAuth (Google, GitHub)
   C. Enterprise SSO (SAML)
   D. All of the above

2. What user roles are needed?
   A. Single role (all users equal)
   B. User + Admin
   C. Custom role system
   D. Other: [specify]

Please respond with your choices (e.g., "1B, 2B").
```

### Step 3.3: Confirm PRD Saved

After PRD skill completes:

```markdown
✅ **Auth PRD complete!**
Saved to: `tasks/prd-auth.md`

Progress: 1 of 5 components done.
Moving to next component: **Tasks**...
```

### Step 3.4: Repeat

Continue until all components have PRDs.

---

### Phase 4: What to Do

1. Present complete collection of artifacts
2. Explain implementation options
3. Mark pipeline as complete

### Phase 4: What to Say

```markdown
🎉 **Project Pipeline Complete!**

All specifications have been generated:

**Architectural Blueprint:**
- `plans/architect_plan.md`

**Product Requirements Documents:**
- `tasks/prd-auth.md`
- `tasks/prd-tasks.md`
- `tasks/prd-boards.md`
- `tasks/prd-teams.md`
- `tasks/prd-notifications.md`

**Next Steps:**
You can now:
1. **Sequential:** Work through PRDs one at a time with a coding agent
2. **Parallel:** Assign each PRD to a separate agent/session
3. **Prioritized:** Start with P0 components (Auth, Tasks, Boards)

My orchestration work is complete. Good luck with implementation! 🚀
```

---

## 📊 Output Artifacts

This skill orchestrates creation of:

| Artifact | Location | Created By |
| :--- | :--- | :--- |
| Architectural Blueprint | `plans/architect_plan.md` | `architect` skill |
| Feature Spec 1 | `tasks/prd-[component-1].md` | `prd` skill |
| Feature Spec 2 | `tasks/prd-[component-2].md` | `prd` skill |
| ... | ... | ... |

---

## 🔑 Key Principles

### Human-in-the-Loop (HITL)

This pipeline uses **guided automation**, not full autonomy:

| Checkpoint | User Action Required |
| :--- | :--- | :--- |
| After Architecture | Review blueprint, confirm component list |
| During each PRD | Answer clarifying questions (A/B/C/D) |
| After all PRDs | Approve collection before implementation |

### Context Isolation

Each PRD agent only receives context for its specific component:

- ✅ Prevents context window overload
- ✅ Enables parallel development later
- ✅ Contains errors to single components

### Progressive Disclosure

The Architect handles "big picture" questions so PRD skills don't re-ask them. The `architect_plan.md` acts as shared context.

---

## 🌟 Complete Example Interaction

See [`references/example_interaction.md`](references/example_interaction.md) for a complete example of a project pipeline session (Trello clone example).

---

## ⛔ Stopping Rules

STOP IMMEDIATELY if you consider:

- Writing any application code
- Making file edits beyond orchestrating `architect` and `prd` skills
- Running tests, builds, or deployments
- Answering PRD questions on behalf of the user

This skill's SOLE responsibility is **project orchestration and PRD collection**.

---

## ✓ Completion Checklist

Before marking pipeline complete, verify:

- [ ] Explained the pipeline process to user
- [ ] Triggered `architect` skill and confirmed blueprint
- [ ] User approved component list before PRD phase
- [ ] Generated PRD for EACH confirmed component
- [ ] User answered questions for EACH PRD (not assumed)
- [ ] Presented complete artifact list to user
- [ ] Did NOT write any application code
