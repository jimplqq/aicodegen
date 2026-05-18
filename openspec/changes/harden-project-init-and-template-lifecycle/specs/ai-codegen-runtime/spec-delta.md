## ADDED Requirements

### Requirement: Workspace Initialization Configuration

The runtime MUST provide an explicit workspace initialization flow that persists project-specific configuration separately from auto-detected analysis data.

#### Scenario: Initialize a target workspace with explicit project settings

- **GIVEN** a user has installed `aicodegen` and entered a target project workspace
- **WHEN** the user runs `aicodegen init` with or without override parameters
- **THEN** the runtime stores a workspace configuration that includes the resolved project settings
- **AND** the runtime stores auto-detected project analysis separately from user-authored configuration
- **AND** the command returns a summary showing the effective initialization result

### Requirement: Configurable Template Root

The runtime MUST support a configurable template storage root for each initialized workspace.

#### Scenario: Use a custom template root for learned scaffold templates

- **GIVEN** a workspace has been initialized with a configured template root
- **WHEN** the runtime learns or reads a template for code generation
- **THEN** it stores and loads the template artifacts from the configured template root
- **AND** it does not require all templates to live under the default `.agent/templates/` path

### Requirement: Template Lifecycle States

The runtime MUST track persistent lifecycle states for each reusable template used by generation tools.

#### Scenario: Track first-run learning through verification

- **GIVEN** a workspace has no prepared template for a generation tool
- **WHEN** the tool is prepared for first-time use
- **THEN** the runtime records state transitions across learning and verification
- **AND** the lifecycle distinguishes at least uninitialized, learning, learned, verifying, verified, and failed states
- **AND** status queries expose the current lifecycle state to callers

### Requirement: Verified First-Run Template Preparation

The runtime MUST verify newly learned templates before allowing them to be used as reusable generation inputs.

#### Scenario: First generation learns and verifies a project-local template

- **GIVEN** a workspace requests generation for a tool that has not yet been verified
- **WHEN** the runtime performs first-run preparation
- **THEN** it learns project-local template inputs from existing project examples
- **AND** it executes template verification before marking the template reusable
- **AND** it marks the template as verified only when verification completes successfully

### Requirement: Reuse of Verified Templates

The runtime MUST reuse verified templates on later generation calls instead of repeating first-run discovery work.

#### Scenario: Later generation skips repeated template learning

- **GIVEN** a workspace already has a verified template for a generation tool
- **WHEN** a later CLI or MCP request triggers generation with that tool
- **THEN** the runtime reuses the verified template artifact
- **AND** it does not repeat project example discovery unless the template has been invalidated or explicitly refreshed

### Requirement: Failure Recording and Recovery Guidance

The runtime MUST record template preparation failures and prevent failed templates from being silently reused.

#### Scenario: Template verification fails during first-run preparation

- **GIVEN** the runtime is learning or verifying a template for first-time use
- **WHEN** verification fails
- **THEN** the runtime records the failure state and error details
- **AND** final generation does not silently proceed as if the template were verified
- **AND** callers receive guidance about retrying, reinitializing, or falling back to a supported recovery path

### Requirement: Shared Lifecycle Between CLI and MCP

CLI-triggered and MCP-triggered generation MUST use the same template lifecycle and verification rules.

#### Scenario: Agent and local CLI prepare templates consistently

- **GIVEN** one caller uses the CLI and another caller uses the MCP server for the same workspace
- **WHEN** either caller triggers template preparation or generation
- **THEN** both callers observe the same persisted workspace configuration, lifecycle state, and verification requirements
- **AND** MCP requests cannot bypass first-run verification that the CLI would enforce

### Requirement: Agent Integration Guidance

The runtime MUST provide a supported way to help users wire the executable into MCP-capable agents.

#### Scenario: Generate integration guidance for a supported agent

- **GIVEN** a user wants to connect an initialized workspace to a supported agent client
- **WHEN** the user requests agent integration guidance from the runtime
- **THEN** the runtime returns the MCP command or configuration guidance required for that client
- **AND** the guidance reflects the initialized workspace and the shared runtime entry point
