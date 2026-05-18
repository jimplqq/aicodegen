# Proposal: add-shared-on-demand-codegen-runtime

## Why

Current AI-assisted code generation is inconsistent across agents, expensive to repeat, and too dependent on each model re-learning the project on every request. The repository needs a shared tool runtime that any compatible agent can invoke, while still adapting generation behavior to each workspace's language, framework, structure, and conventions.

## What Changes

- Add an OpenSpec capability for a shared AI code generation runtime that serves multiple agents.
- Define project analysis, stack detection, template lifecycle, verification, and on-demand execution requirements.
- Start implementation with a Python-based local runtime that exposes CLI entry points and a future MCP entry point.
- Persist project-specific state under `.agent/` so the executable can remain ephemeral while knowledge survives between runs.

## Impact

- Affected capability: `ai-codegen-runtime`
- New implementation scaffold in Python for local execution, project initialization, and stack detection
- Future agent integrations can reuse the same executable instead of embedding generator logic per agent
