# Discovery Questions Bank

Organized by domain. Select the most relevant domains based on project type and engagement mode. You don't need every question — pick 2-4 per domain that are most valuable given what you already know.

## Contents

- [Vision & Problem Space](#vision--problem-space)
- [Users & Stakeholders](#users--stakeholders)
- [Technical Stack & Constraints](#technical-stack--constraints)
- [Data Architecture](#data-architecture)
- [API & Integration Design](#api--integration-design)
- [Security & Auth](#security--auth)
- [Performance & Scaling](#performance--scaling)
- [Error Handling & Resilience](#error-handling--resilience)
- [Testing Strategy](#testing-strategy)
- [Deployment & Infrastructure](#deployment--infrastructure)
- [Observability & Monitoring](#observability--monitoring)

---

## Vision & Problem Space

*Always relevant. Start here.*

- What specific problem does this solve, and who feels that pain today?
- What does the user currently do instead (workaround, competitor, manual process)?
- What would make this project a clear success? Can you quantify it?
- What is explicitly out of scope for the initial version?
- Are there hard deadlines, budget constraints, or team size limitations?
- Is this replacing an existing system? If so, what must be preserved?

## Users & Stakeholders

*Critical for greenfield. Lighter for internal tools.*

- Who are the primary users? How technically sophisticated are they?
- How many concurrent users do you expect at launch? At scale?
- Are there different user roles with different permissions?
- Will this be used on mobile, desktop, or both?
- Are there accessibility requirements (WCAG compliance level)?

## Technical Stack & Constraints

*Critical for greenfield. For features/refactors, validate against existing stack.*

- Are there existing technology choices that must be respected?
- What languages/frameworks does the team have experience with?
- Are there licensing constraints (open-source only, commercial OK)?
- What is the deployment target (cloud, on-prem, local, embedded)?
- Is there an existing CI/CD pipeline to integrate with?
- Are there performance requirements that constrain technology choices (GPU, real-time, low latency)?

**Probing questions when user says "no preference":**

- What have you used before that you liked working with?
- Is there a technology your team already knows well?
- Are there constraints I should know about (cost, licensing, platform)?

## Data Architecture

*Always relevant. Depth scales with data complexity.*

- What are the core data entities and their relationships?
- How much data do you expect (rows, file sizes, growth rate)?
- Does data need to be queryable, or is it mostly write-then-read?
- Are there existing data sources to integrate with or migrate from?
- What is the data retention policy?
- Do you need full-text search? Real-time queries? Analytics?
- Is eventual consistency acceptable, or do you need strong consistency?

## API & Integration Design

*Critical for features and multi-system architectures.*

- What external systems must this integrate with?
- Are there existing APIs you need to consume or be compatible with?
- What protocol is appropriate (REST, GraphQL, gRPC, WebSocket)?
- Do integrations need to work offline or handle degraded connectivity?
- Are there rate limits or quotas on external APIs?
- Will this expose a public API for third-party consumption?

## Security & Auth

*Always relevant — probe even when user doesn't mention it.*

- What authentication method is appropriate (OAuth, API keys, local-only, SSO)?
- Are there different authorization levels (admin, editor, viewer)?
- What data sensitivity classification applies (public, internal, PII, regulated)?
- Are there compliance requirements (GDPR, HIPAA, SOC2, PCI)?
- What are the trust boundaries (browser ↔ server, server ↔ database, server ↔ external API)?
- How should secrets be managed (env vars, vault, config file)?

## Performance & Scaling

*Important when load is non-trivial or latency-sensitive.*

- What are the response time expectations for key operations?
- What is the expected concurrent load (requests/second, active users)?
- Are there operations that are inherently slow (ML inference, large file processing)?
- What caching strategy is appropriate? What can be cached safely?
- Does this need to scale horizontally, or is vertical scaling sufficient?
- Are there specific bottlenecks you're already aware of?

## Error Handling & Resilience

*Always relevant. Often underspecified by users.*

- What happens when an external dependency is unavailable?
- Which operations must be atomic (all-or-nothing)?
- How should partial failures be communicated to the user?
- Do long-running operations need to survive process restarts?
- What is the retry strategy for failed operations?
- What does graceful degradation look like for this system?

## Testing Strategy

*Always relevant. Depth scales with system criticality.*

- What testing levels are needed (unit, integration, e2e, performance)?
- Are there existing test patterns or frameworks in the codebase?
- What is the coverage target for critical paths?
- Are there operations that are expensive to test (GPU, external APIs, large data)?
- How should test data be managed (fixtures, factories, seeds)?
- Is there a CI pipeline where tests must pass?

## Deployment & Infrastructure

*Critical for greenfield and refactors. Lighter for features within existing infra.*

- Where will this run (cloud provider, on-prem, local machine, edge)?
- Is containerization required or preferred?
- How are environments managed (dev, staging, production)?
- What is the deployment mechanism (CI/CD, manual, installer)?
- Are there uptime requirements (SLA)?
- How will the application be monitored and updated?

## Observability & Monitoring

*Important for production systems. Lighter for local tools.*

- What logging level and structure is needed?
- Are there metrics that must be tracked (latency, error rates, queue depth)?
- How should alerts be triggered and routed?
- Is distributed tracing needed?
- What existing monitoring infrastructure can be leveraged?
