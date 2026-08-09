---
name: function-trace
description: "Trace functions, methods, endpoints, class behavior, and feature flow through a codebase when investigating callers, callees, entry points, execution paths, indirect wiring, or dead code. Triggers on: trace function, where is this called, follow execution, call hierarchy, unused code, why does this exist, how does this work."
---

# Function Trace

## The Job

1. Identify the exact symbol, feature, or behavior to trace.
2. Find the primary definitions, wrappers, adapters, and entry points.
3. Trace upward through callers, triggers, and framework wiring.
4. Trace downward through important callees and side effects.
5. Assess reachability as active, indirect, ambiguous, or likely dead.
6. Verify external behavior only when repository evidence is insufficient.
7. Return a compact markdown trace that explains how the target is reached, used, and connected.

## Constraints

  - DO NOT edit existing files or create new files.
  - DO NOT stop at the first definition or first caller if deeper tracing is needed to explain behavior.
  - DO NOT speculate about framework or library behavior when a code search or web lookup can verify it.
  - DO NOT present a shallow summary when the request asks for full hierarchy or issue hunting.
  - ONLY use web research when it helps explain external APIs, libraries, framework conventions, or generated behavior that is not clear from the repository alone.

## Investigation Rules

  - Prefer repository evidence over assumptions.
  - If the request is ambiguous, state that and trace the most likely match first.
  - Distinguish direct calls, indirect calls, and framework wiring.
  - Distinguish confirmed dead code from code that may be dynamically referenced.
  - Call out async boundaries, background work, recursion, event loops, pass-through layers, naming mismatches, and suspicious dead ends.
  - If the trace fans out widely, prioritize the paths that affect the reported behavior and summarize lower-value branches briefly.
  - Prefer official or primary sources for external context.

## Gotchas

  - A function with no obvious call sites may still be framework-wired, registered dynamically, imported for side effects, or referenced by name.
  - The first definition found is often not the true execution anchor. Wrappers, adapters, decorators, and event wiring frequently hide the real path.
  - Wide call graphs are rarely equally important. Follow the branches that affect the reported behavior first.
  - External framework behavior should be verified, not assumed.

## Output Format

Return these sections in order, in markdown format as a reply.

### Target

  - The symbol, feature, or behavior traced.
  - The main file locations that anchor the trace.

### Trace Summary

  - A concise explanation of what this code does and how execution reaches it.

### Upstream Callers

  - Confirmed callers, triggers, or entry points.
  - For each one, explain how control reaches the target.

### Downstream Callees

  - Important functions, services, or side effects the target depends on.
  - Explain which branches are central versus incidental.

### Reachability And Status

  - State whether the target is actively used, indirectly wired, ambiguous, or likely dead.
  - If it appears unused, explain what evidence was checked and what dynamic paths could still exist.

### External Context

  - Include only if web research materially clarified a library, framework, or runtime behavior.

### Findings

  - List the most relevant issues, oddities, or debugging leads uncovered by the trace.
  - Be explicit about uncertainty, missing evidence, or places where runtime inspection would be needed.

## Stopping Rules

STOP IMMEDIATELY if you consider:

  - Writing or editing existing files.
  - Creating new files.

This skill's SOLE responsibility is tracing code behavior and explaining how a target is reached, used, and connected.

## Checklist

Before completing, verify:

  - [ ] The traced target is clearly identified.
  - [ ] The primary definitions and entry points were checked.
  - [ ] Upstream callers and downstream callees were separated clearly.
  - [ ] Reachability was assessed with explicit evidence.
  - [ ] External context was included when it materially clarified the trace.
  - [ ] Uncertainty and runtime-only gaps were stated explicitly.
  - [ ] No code edits or speculative fixes were mixed into the trace.