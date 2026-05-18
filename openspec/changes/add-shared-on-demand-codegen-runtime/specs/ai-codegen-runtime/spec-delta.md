## ADDED Requirements

### Requirement: Shared Runtime Across Agents
WHEN a compatible AI agent requests code-generation capability for a workspace,
the system SHALL expose the capability through a shared runtime instead of requiring agent-specific generator implementations.

#### Scenario: CLI and agent integrations use the same runtime
GIVEN the runtime is installed on a developer machine
WHEN a user invokes the CLI directly or an agent launches the MCP entry point
THEN both entry points SHALL use the same workspace analysis, template state, and tool registry behavior.

### Requirement: On-Demand Execution
WHEN no code-generation request is active,
the system SHALL NOT require a permanently running background service.

#### Scenario: Ephemeral execution with persisted state
GIVEN a workspace has already been initialized
WHEN an agent invokes the runtime for a single request
THEN the runtime SHALL load project state from disk, handle the request, and allow the process to exit without losing learned project context.

### Requirement: Workspace Stack Detection
WHEN a workspace is initialized or re-analyzed,
the system SHALL detect the primary language, build tool, framework, and relevant generation hints from repository files.

#### Scenario: Detect common backend and application stacks
GIVEN a workspace containing files such as `pom.xml`, `build.gradle`, `package.json`, `requirements.txt`, `pyproject.toml`, or `go.mod`
WHEN the analysis step runs
THEN the runtime SHALL classify the workspace language and major toolchain
AND persist the result as structured project analysis data for later generation requests.

### Requirement: Project-Isolated Persistent State
WHEN the runtime learns how a workspace is structured,
the system SHALL persist project-specific analysis, tool configuration, and template artifacts under the workspace rather than global process memory.

#### Scenario: Multiple projects keep separate generation behavior
GIVEN two workspaces with different languages or code conventions
WHEN the runtime initializes each workspace
THEN each workspace SHALL maintain its own `.agent/` state
AND generation requests in one workspace SHALL NOT reuse templates or rules from the other unless explicitly imported.

### Requirement: Verified Template Lifecycle
WHEN a generation tool is first enabled for a workspace,
the system SHALL move the tool through initialization, debug, and verification states before the tool is considered production-ready.

#### Scenario: Unverified tools cannot be used for final generation
GIVEN a tool has generated templates but has not passed validation
WHEN an agent requests final code generation from that tool
THEN the runtime SHALL reject the request as not ready
AND direct the caller to the debug or verification workflow.

### Requirement: Installation Separate from Workspace Initialization
WHEN a developer installs the runtime executable,
the system SHALL make the program available machine-wide while deferring workspace adaptation until initialization runs inside a project.

#### Scenario: Global executable with per-project setup
GIVEN the runtime executable is available on PATH
WHEN a user enters a new workspace and runs initialization
THEN the runtime SHALL create project-local state files and directories
AND SHALL NOT require reinstalling the executable for each workspace.
