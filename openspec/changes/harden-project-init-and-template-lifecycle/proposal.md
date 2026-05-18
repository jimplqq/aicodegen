# Proposal: harden-project-init-and-template-lifecycle

## Why

The current `aicodegen` runtime already provides a usable local executable, project detection, template learning, CRUD generation, and an MCP server. However, it does not yet deliver the full workflow the product is aiming for:

- users should be able to install `aicodegen` once and initialize each target workspace with explicit project settings
- first-time generation should learn project-local templates, verify they are safe to reuse, and persist the result
- later generation calls from CLI and AI agents should reuse the verified template path instead of repeating discovery work

Today, several gaps make that workflow incomplete:

- `init` behaves more like automatic detection than a real project initialization command
- template storage is fixed to `.agent/templates/` instead of a configurable template root
- template learning stores example references, but does not model a verified template lifecycle
- MCP and CLI share runtime code, but the first-run validation and recovery flow is still missing

Without these pieces, the first-time user experience is fragile and the promise of "learn once, reuse safely later" is not yet guaranteed.

## What Changes

- Add explicit workspace configuration for initialized projects, including template root, project stack overrides, script commands, validation commands, and agent integration hints.
- Upgrade `aicodegen init` into a true project initialization entry point that combines detection with user-specified configuration.
- Introduce a template lifecycle state model covering uninitialized, learning, verifying, verified, and failed states.
- Extend template learning so it produces persisted template metadata and reusable template artifacts instead of only saving example-file snapshots.
- Add a first-run template verification flow before templates are considered reusable for final generation.
- Define failure handling and recovery behavior for template learning and validation.
- Add agent integration helper commands so Kimi, Codex, or other MCP-capable clients can adopt the runtime more consistently.
- Expand automated coverage around init, template lifecycle, and first-run versus steady-state generation behavior.

## Impact

- Affected capability: `ai-codegen-runtime`
- Affected implementation areas:
  - CLI initialization flow
  - workspace storage and configuration
  - template manager and template metadata
  - runtime generation lifecycle
  - MCP integration ergonomics
  - end-to-end verification coverage
- This change keeps the existing Python runtime architecture, but hardens it into a project-oriented workflow that better matches the intended product behavior.
