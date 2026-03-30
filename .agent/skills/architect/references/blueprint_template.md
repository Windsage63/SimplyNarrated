# Blueprint Template

The complete template for `plans/architect_plan.md`. Include all sections for greenfield projects. For features and refactors, include only relevant sections — see the mode guidance below.

## Contents

- [Mode Guidance](#mode-guidance)
- [Template](#template) — Sections 1-16: Executive Summary, Technical Stack, Architectural Overview, Core Decisions, Components, Data, API, Security, Error Handling, Testing, Performance, Deployment, Requirements, Roadmap, Risks, Open Questions

---

## Mode Guidance

**Greenfield:** Use all sections. Every layer of the stack needs explicit decisions.

**Feature/Module:** Focus on sections 1, 4-5 (new components), 7 (API changes), 8 (security impact), 13-15 (requirements, roadmap, risks). Reference existing stack from section 2 briefly rather than re-specifying it.

**Refactor:** Replace sections 3 and 14 with a dedicated "Current State → Target State" analysis and "Migration Plan" with incremental steps, rollback strategy, and backwards compatibility notes.

---

## Template

```markdown
# [Project Title] — Architectural Blueprint

> **Engagement mode:** [Greenfield | Feature/Module | Refactor]
> **Date:** [YYYY-MM-DD]
> **Status:** Draft | Approved

## 1. Executive Summary

[2-3 sentences: What is being built, the core architectural approach, and the key constraint or design principle driving decisions.]

## 2. Technical Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | [Tech] | [Why this over alternatives] |
| Backend | [Tech] | [Why this over alternatives] |
| Database | [Tech] | [Why this over alternatives] |
| Auth | [Tech] | [Why this over alternatives] |
| Infrastructure | [Tech] | [Why this over alternatives] |
| [Other layers as needed] | [Tech] | [Rationale] |

## 3. Architectural Overview

### System Context

[1-2 paragraphs: How does this system fit into its environment? What are its external boundaries? What does it interact with?]

### Component Interaction

[ASCII diagram or structured description showing how major components communicate. Include protocols and data flow direction.]

### Key Architectural Patterns

[Name the dominant pattern(s): pipeline, event-driven, layered, hexagonal, CQRS, etc. Explain why this pattern fits the problem.]

## 4. Core Architectural Decisions

Record each significant decision in ADR format. Typically 3-6 decisions for a new project.

### ADR-1: [Decision Title]

- **Choice:** [What we decided]
- **Rationale:** [Why this choice over alternatives]
- **Alternatives considered:** [What else was evaluated]
- **Trade-offs:** [What we're giving up or accepting as a cost]

### ADR-2: [Decision Title]

[Same format...]

## 5. Component Breakdown

| Component | Description | Priority | Dependencies |
|-----------|-------------|----------|--------------|
| [Name] | [What it does, in one sentence] | P0/P1/P2 | [Which components it depends on] |
| [Name] | [Purpose] | P0/P1/P2 | [Dependencies] |

P0 = Must have for MVP. P1 = Important, build after P0. P2 = Nice-to-have, defer if needed.

## 6. Data Architecture

### Storage Model

[Describe where data lives: databases, filesystem, caches, external services.]

### Core Schema

[Key tables/collections, their purpose, and important fields. Use a table or brief ERD description.]

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| [Name] | [What it stores] | [Important columns/fields] |

### Data Flow

[Numbered sequence showing how data moves through the system for the 1-2 most critical operations.]

### Migration Strategy

[How will schema evolve? Versioned migrations, backwards compatibility approach.]

## 7. API Design

### Conventions

[URL structure, request/response format, pagination, error format, versioning strategy.]

### Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| [HTTP method] | [Path] | [What it does] |

[Only list the most important endpoints — aim for 8-15 covering the core operations.]

## 8. Security Architecture

### Threat Model

[What are the trust boundaries? What attack vectors are relevant? How does the auth model work?]

### Data Protection

[Encryption at rest/in transit, PII handling, secrets management, input validation approach.]

### Compliance

[Relevant standards: GDPR, HIPAA, SOC2, or "N/A — internal tool / local app".]

## 9. Error Handling & Resilience

### Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| [What can go wrong] | [How we detect it] | [How we recover] |

### Resilience Patterns

[Retry strategy, circuit breakers, graceful degradation, idempotency guarantees — whichever apply.]

## 10. Testing Strategy

| Level | Scope | Tools | Coverage Target |
|-------|-------|-------|-----------------|
| Unit | [What's tested] | [Framework] | [Target %] |
| Integration | [What's tested] | [Framework + fixtures] | [Target] |
| E2E | [Critical paths] | [Framework] | [Target] |

### Test Data Management

[How test data is created, managed, and cleaned up.]

## 11. Performance & Scaling

### Expected Load

[Quantified: users, requests/sec, data volume, growth projections.]

### Optimization Strategy

[Caching, indexing, pooling, async processing — specific to this system's bottlenecks.]

### Known Bottlenecks

[Operations that will be slow and how they're mitigated.]

## 12. Deployment & Infrastructure

### Runtime Environment

[Where it runs, how it starts, what it depends on externally.]

### Environments

| Environment | Purpose | Key Differences |
|-------------|---------|-----------------|
| Development | [Purpose] | [Config differences] |
| Production | [Purpose] | [Config differences] |
| Testing | [Purpose] | [Config differences] |

### CI/CD

[Build, test, deploy pipeline. Manual steps if any.]

## 13. Requirements & Acceptance Criteria

### Functional Requirements

- [ ] FR-1: [Specific, testable requirement]
- [ ] FR-2: [Requirement]

### Non-Functional Requirements

- [ ] NFR-1: [Performance/reliability/usability requirement with measurable criteria]
- [ ] NFR-2: [Requirement]

## 14. Implementation Roadmap

### Phase 1: [Name] (P0)

1. **[Component]** — [Why first, what it unblocks]
2. **[Component]** — [Depends on #1 because...]

### Phase 2: [Name] (P0-P1)

3. **[Component]** — [Built on Phase 1 foundation]

### Phase 3: [Name] (P1-P2)

4. **[Component]** — [Enhancement layer]

[Each phase should be deployable/testable independently where possible.]

## 15. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [What could go wrong] | Low/Med/High | Low/Med/High | [Concrete action to reduce risk] |

## 16. Open Questions

- [ ] [Unresolved decision or unknown that needs follow-up]
- [ ] [Item requiring user input, research, or prototyping]
```
