from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .generator import CrudGenerator
from .runtime import RuntimeService


JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


def _tool_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="project_status",
            description="Return the ai-codegen workspace status and detected project profile.",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="ensure_template",
            description="Ensure a reusable project template exists for the specified tool.",
            input_schema={
                "type": "object",
                "properties": {
                    "tool": {
                        "type": "string",
                        "description": "Tool name to prepare. Defaults to crud_generator.",
                        "default": "crud_generator",
                    }
                },
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="generate_entity",
            description="Generate a single domain/entity Java file using the learned workspace template.",
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity class name such as DeviceLedger."},
                    "comment": {"type": "string", "description": "Optional human-readable feature name."},
                },
                "required": ["entity"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="generate_crud",
            description="Generate CRUD scaffold files for an entity using the learned workspace template.",
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity class name such as DeviceLedger."},
                    "comment": {"type": "string", "description": "Optional human-readable feature name."},
                },
                "required": ["entity"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="generate_feature",
            description="High-level feature generator. Infers the entity name, ensures templates, then generates entity and CRUD files.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Natural-language feature name such as 设备台账."},
                    "entity": {"type": "string", "description": "Optional explicit entity class name."},
                    "spec": {
                        "type": "object",
                        "description": "Optional structured feature specification with table_name, route_path, permission_prefix, and fields.",
                    },
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        ),
    ]


class McpServer:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.runtime = RuntimeService(workspace)
        self._tools = {tool.name: tool for tool in _tool_definitions()}

    def serve(self) -> int:
        while True:
            message = self._read_message()
            if message is None:
                return 0
            response = self._handle_message(message)
            if response is not None:
                self._write_message(response)

    def _read_message(self) -> dict[str, Any] | None:
        headers: dict[str, str] = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            if line in (b"\r\n", b"\n"):
                break
            decoded = line.decode("utf-8").strip()
            if ":" not in decoded:
                continue
            key, value = decoded.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", "0"))
        if content_length <= 0:
            return None
        body = sys.stdin.buffer.read(content_length)
        if not body:
            return None
        return json.loads(body.decode("utf-8"))

    def _write_message(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
        sys.stdout.buffer.write(header)
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()

    def _handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        request_id = message.get("id")

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return self._success(
                request_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "ai-codegen", "version": "0.1.0"},
                },
            )
        if method == "ping":
            return self._success(request_id, {})
        if method == "tools/list":
            return self._success(
                request_id,
                {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.input_schema,
                        }
                        for tool in self._tools.values()
                    ]
                },
            )
        if method == "tools/call":
            try:
                result = self._call_tool(message.get("params", {}))
            except Exception as exc:  # noqa: BLE001
                return self._success(
                    request_id,
                    {
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    },
                )
            return self._success(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
                    "structuredContent": result,
                    "isError": False,
                },
            )

        if request_id is None:
            return None
        return self._error(request_id, -32601, f"Method not found: {method}")

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments", {}) or {}

        if name == "project_status":
            return self.runtime.status()
        if name == "ensure_template":
            tool_name = str(arguments.get("tool", "crud_generator"))
            return self.runtime.ensure_template(tool_name)
        if name == "generate_entity":
            tools_config = self.runtime._ensure_tools_config(self.runtime.detector.detect())
            generated = CrudGenerator(self.workspace, tools_config).generate_entity(
                str(arguments["entity"]),
                comment=arguments.get("comment"),
            )
            return {
                "workspace": str(self.workspace),
                "generated_file": {"kind": generated.kind, "path": str(generated.path)},
            }
        if name == "generate_crud":
            tools_config = self.runtime._ensure_tools_config(self.runtime.detector.detect())
            generated = CrudGenerator(self.workspace, tools_config).generate(
                str(arguments["entity"]),
                comment=arguments.get("comment"),
            )
            return {
                "workspace": str(self.workspace),
                "generated_files": [
                    {"kind": item.kind, "path": str(item.path)}
                    for item in generated
                ],
            }
        if name == "generate_feature":
            return self.runtime.generate_feature(
                str(arguments["name"]),
                entity_name=arguments.get("entity"),
                spec_data=arguments.get("spec"),
            )
        raise ValueError(f"Unknown tool: {name}")

    def _success(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {"code": code, "message": message},
        }


def run_stdio_server(workspace: Path) -> int:
    server = McpServer(workspace)
    return server.serve()
