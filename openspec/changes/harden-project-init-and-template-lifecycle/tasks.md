# Tasks: harden-project-init-and-template-lifecycle

## 1. Workspace Configuration

- [x] 1.1 Add a workspace configuration model persisted under `.agent/`
- [x] 1.2 Define fields for template root, stack overrides, script commands, validation commands, generation defaults, and agent integration hints
- [x] 1.3 Keep detected analysis data separate from user-authored workspace configuration

## 2. Initialization Flow

- [x] 2.1 Extend `aicodegen init` to create default workspace configuration
- [x] 2.2 Support explicit init overrides for language, framework, template root, build command, and test command
- [x] 2.3 Return a readable initialization summary that shows detected values, configured values, and resulting storage paths

## 3. Storage and Template Path Handling

- [x] 3.1 Refactor storage so template paths are read from workspace configuration instead of being hard-coded
- [x] 3.2 Add persistence helpers for workspace configuration and template metadata
- [x] 3.3 Preserve compatibility with existing `.agent/project_analysis.json` and `tools.json` files

## 4. Template Lifecycle State Model

- [x] 4.1 Introduce lifecycle states for uninitialized, learning, learned, verifying, verified, and failed
- [x] 4.2 Persist lifecycle state and error details per tool template
- [x] 4.3 Expose lifecycle state through `aicodegen status` and MCP status responses

## 5. Template Learning and Artifact Persistence

- [x] 5.1 Upgrade first-run learning to persist structured template artifacts and metadata
- [x] 5.2 Record the source examples, learning strategy, analysis snapshot, and template version
- [x] 5.3 Ensure later generation calls reuse learned template artifacts instead of repeating discovery

## 6. Template Verification

- [ ] 6.1 Add a verification phase after first-run template learning
- [ ] 6.2 Verify generated files, placeholder substitution, and target paths
- [ ] 6.3 Support optional build or test command validation from workspace configuration
- [ ] 6.4 Mark templates as verified only after verification succeeds

## 7. Failure Handling and Recovery

- [ ] 7.1 Record learning and verification failures with actionable error information
- [ ] 7.2 Define retry and fallback behavior for failed template preparation
- [ ] 7.3 Prevent final generation from silently reusing failed or unverified templates

## 8. Agent Integration Helpers

- [ ] 8.1 Add helper commands for generating MCP configuration guidance for supported agents
- [ ] 8.2 Add a doctor-style command to check init state, template readiness, and runtime wiring
- [ ] 8.3 Ensure MCP-triggered generation uses the same lifecycle and validation rules as CLI-triggered generation

## 9. Testing

- [ ] 9.1 Add end-to-end tests for init, first-run learning, verification, and steady-state reuse
- [ ] 9.2 Add tests for custom template roots and failure recovery flows
- [ ] 9.3 Add MCP-path coverage for first-run and repeated generation scenarios
