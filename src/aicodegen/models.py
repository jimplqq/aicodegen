from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass
class ToolEntry:
    status: str = "uninitialized"
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_error: str = ""


@dataclass
class ToolsConfig:
    enabled_tools: list[str] = field(default_factory=list)
    suggested_tools: list[str] = field(default_factory=list)
    project_profile: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, ToolEntry] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled_tools": self.enabled_tools,
            "suggested_tools": self.suggested_tools,
            "project_profile": self.project_profile,
            "tools": {
                name: asdict(entry)
                for name, entry in self.tools.items()
            },
        }

    @classmethod
    def from_path(cls, path: Path) -> "ToolsConfig":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        tools = {
            name: ToolEntry(
                status=str(entry.get("status", "uninitialized")),
                config=dict(entry.get("config", {})),
                metadata=dict(entry.get("metadata", {})),
                last_error=str(entry.get("last_error", "")),
            )
            for name, entry in data.get("tools", {}).items()
        }
        return cls(
            enabled_tools=list(data.get("enabled_tools", [])),
            suggested_tools=list(data.get("suggested_tools", [])),
            project_profile=dict(data.get("project_profile", {})),
            tools=tools,
        )


@dataclass
class ProjectAnalysis:
    language: str = "unknown"
    build_tool: str = "unknown"
    framework: str = "unknown"
    package_manager: str = "unknown"
    test_framework: str = "unknown"
    java_version: str = "unknown"
    spring_boot_version: str = "unknown"
    orm: str = "unknown"
    architecture: str = "unknown"
    modules: list[str] = field(default_factory=list)
    base_package: str = "unknown"
    libraries: dict[str, bool] = field(default_factory=dict)
    conventions: dict[str, Any] = field(default_factory=dict)
    hints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_to(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


@dataclass
class WorkspaceConfig:
    language: str = ""
    framework: str = ""
    template_root: str = ".agent/templates"
    stack_overrides: dict[str, str] = field(default_factory=dict)
    script_commands: dict[str, str] = field(default_factory=dict)
    validation_commands: dict[str, str] = field(default_factory=dict)
    generation_defaults: dict[str, Any] = field(default_factory=dict)
    agent_integration: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceConfig":
        return cls(
            language=str(data.get("language", "")),
            framework=str(data.get("framework", "")),
            template_root=str(data.get("template_root", ".agent/templates")),
            stack_overrides={
                str(name): str(value)
                for name, value in dict(data.get("stack_overrides", {})).items()
            },
            script_commands={
                str(name): str(value)
                for name, value in dict(data.get("script_commands", {})).items()
            },
            validation_commands={
                str(name): str(value)
                for name, value in dict(data.get("validation_commands", {})).items()
            },
            generation_defaults=dict(data.get("generation_defaults", {})),
            agent_integration=dict(data.get("agent_integration", {})),
        )

    @classmethod
    def from_path(cls, path: Path) -> "WorkspaceConfig":
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def write_to(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


@dataclass
class FieldSpec:
    name: str
    type: str
    column: str
    comment: str = ""
    query: str = ""
    excel: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldSpec":
        return cls(
            name=str(data["name"]),
            type=str(data["type"]),
            column=str(data.get("column") or data["name"]),
            comment=str(data.get("comment", "")),
            query=str(data.get("query", "")),
            excel=bool(data.get("excel", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FeatureSpec:
    name: str
    entity: str
    comment: str = ""
    table_name: str = ""
    route_path: str = ""
    permission_prefix: str = ""
    bo_name: str = ""
    vo_name: str = ""
    bo_package: str = ""
    vo_package: str = ""
    response_wrapper: str = "AjaxResult"
    use_result_model: bool = False
    use_slf4j: bool = True
    use_pre_authorize: bool = True
    use_log: bool = True
    fields: list[FieldSpec] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeatureSpec":
        return cls(
            name=str(data["name"]),
            entity=str(data["entity"]),
            comment=str(data.get("comment", "")),
            table_name=str(data.get("table_name", "")),
            route_path=str(data.get("route_path", "")),
            permission_prefix=str(data.get("permission_prefix", "")),
            bo_name=str(data.get("bo_name", "")),
            vo_name=str(data.get("vo_name", "")),
            bo_package=str(data.get("bo_package", "")),
            vo_package=str(data.get("vo_package", "")),
            response_wrapper=str(data.get("response_wrapper", "AjaxResult")),
            use_result_model=bool(data.get("use_result_model", False)),
            use_slf4j=bool(data.get("use_slf4j", True)),
            use_pre_authorize=bool(data.get("use_pre_authorize", True)),
            use_log=bool(data.get("use_log", True)),
            fields=[FieldSpec.from_dict(item) for item in data.get("fields", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["fields"] = [field.to_dict() for field in self.fields]
        return payload
