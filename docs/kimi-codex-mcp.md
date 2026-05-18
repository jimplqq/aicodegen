# ai-codegen MCP Integration

## Goal

Let an MCP-capable agent call `ai-codegen` automatically when the user says something like:

`新增设备台账功能`

The high-level tool to call is:

- `generate_feature`

It will automatically:

1. detect the current project
2. ensure the learned template exists
3. infer the entity name
4. generate the entity
5. generate CRUD scaffold files

## Start the MCP server

PowerShell:

```powershell
aicodegen --workspace C:\workspace\java_workspace\emlight mcp
```

Git Bash:

```bash
aicodegen --workspace /c/workspace/java_workspace/emlight mcp
```

## Exposed MCP tools

- `project_status`
- `ensure_template`
- `generate_entity`
- `generate_crud`
- `generate_feature`

## Recommended agent behavior

When the user asks to add a new feature, scaffold CRUD code, create a new module, or generate basic project files:

1. call `project_status`
2. if needed, call `ensure_template`
3. call `generate_feature`

## Recommended natural-language trigger rule

Put a rule like this into the agent system prompt or tool policy:

> When the user asks to add a feature, create CRUD code, scaffold backend files, or generate project boilerplate, prefer the `generate_feature` MCP tool instead of writing the files manually.

## Example MCP tool call

```json
{
  "name": "generate_feature",
  "arguments": {
    "name": "设备台账"
  }
}
```

## Expected result

For the `emlight` workspace, `generate_feature` should infer:

- feature name: `设备台账`
- entity name: `DeviceLedger`
- module: `ruoyi-em`

And generate:

- `domain`
- `mapper`
- `service`
- `service impl`
- `controller`
- `mapper xml`

## Codex-style MCP server config

Use a server entry similar to:

```json
{
  "mcpServers": {
    "ai-codegen-emlight": {
      "command": "aicodegen",
      "args": [
        "--workspace",
        "C:\\workspace\\java_workspace\\emlight",
        "mcp"
      ]
    }
  }
}
```

If the client runs inside Git Bash or expects POSIX paths, use:

```json
{
  "mcpServers": {
    "ai-codegen-emlight": {
      "command": "aicodegen",
      "args": [
        "--workspace",
        "/c/workspace/java_workspace/emlight",
        "mcp"
      ]
    }
  }
}
```

## Kimi integration note

If the Kimi client supports custom MCP servers, point it to the same command and let the model call `generate_feature`.

If the Kimi product you are using does not support custom MCP servers yet, then natural-language understanding will work, but actual automatic file generation will not happen until MCP or local tool execution is available in that client.
