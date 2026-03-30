# PRD Output Template

Use this template when generating PRDs. Adapt sections based on engagement mode — not every section is needed for every PRD.

## Section Applicability

| Section | New Feature | Refactor/Improvement | Blueprint Implementation |
| --------- | :-----------: | :--------------------: | :------------------------: |
| Introduction | Always | Always | Always |
| Goals | Always | Always | Always |
| User Stories | Always | If user-facing | Always |
| Functional Requirements | Always | Always | Always |
| Non-Goals | Always | Always | Always |
| Migration/Compatibility | Rarely | Always | Sometimes |
| Technical Considerations | If complex | Always | Reference blueprint |
| Implementation Roadmap | Always | Always | Always |
| Success Metrics | Always | Always | Always |
| Open Questions | Always | Always | Always |

## Template

````markdown
# PRD: [Feature/Change Name]

## Introduction

[2-3 sentences: what is being built/changed and why. Reference the source blueprint section if this PRD was derived from one.]

## Goals

- [Specific, measurable objective]
- [Another objective]
- [Keep to 3-6 goals]

## User Stories

### US-001: [Title]

**Description:** As a [user/role], I want [capability] so that [benefit].

**Acceptance Criteria:**
- [ ] [Specific, verifiable criterion]
- [ ] [Another criterion]
- [ ] [Each criterion should be independently testable]

### US-002: [Title]

**Description:** As a [user/role], I want [capability] so that [benefit].

**Acceptance Criteria:**

- [ ] [Criterion]

## Functional Requirements

- FR-1: [The system must/shall...]
- FR-2: [When X happens, the system must...]
- FR-3: [Be explicit and unambiguous]

## Non-Goals (Out of Scope)

- [What this will NOT include]
- [Features deferred to future work]
- [Boundaries that prevent scope creep]

## Migration & Compatibility

> Include this section for refactors and changes that touch existing functionality.

- **Breaking changes:** [List any, or "None"]
- **Migration path:** [Steps to transition from current to new behavior]
- **Rollback strategy:** [How to revert if problems arise]

## Technical Considerations

- [Known constraints or dependencies]
- [Integration points with existing components]
- [Performance requirements or concerns]
- [Reference specific blueprint sections if applicable]

## Implementation Roadmap

| Phase | Stories/Tasks | Dependencies | Notes |
|-------|--------------|--------------|-------|
| 1. [Name] | US-001 | None | [Context] |
| 2. [Name] | US-002, US-003 | Phase 1 | [Context] |
| 3. [Name] | US-004 | Phase 2 | [Context] |

## Success Metrics

- [How will success be measured?]
- [Quantitative where possible]

## Open Questions

- [ ] [Remaining question needing clarification]
- [ ] [Decision that was deferred]
````
