from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from .models import ProjectAnalysis, ToolEntry, ToolsConfig
from .storage import WorkspaceStorage


class TemplateManager:
    def __init__(self, workspace: Path, storage: WorkspaceStorage) -> None:
        self.workspace = workspace
        self.storage = storage

    def ensure_template(self, tool_name: str, analysis: ProjectAnalysis, tools_config: ToolsConfig) -> dict[str, object]:
        template_path = self.storage.template_path(tool_name)
        tool_entry = tools_config.tools.setdefault(tool_name, ToolEntry())
        learned = False
        if not template_path.exists():
            tool_entry.status = "learning"
            payload = self._learn_template(tool_name, analysis, tools_config)
            payload["template_version"] = 1
            payload["learned_at"] = datetime.now(UTC).isoformat()
            payload["lifecycle_state"] = "learned"
            template_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            learned = True
        else:
            payload = json.loads(template_path.read_text(encoding="utf-8"))

        lifecycle_state = str(payload.get("lifecycle_state", "learned"))
        tool_entry.status = lifecycle_state
        tool_entry.last_error = ""
        tool_entry.metadata = {
            "template_path": str(template_path),
            "strategy": payload.get("strategy", "generic"),
            "template_version": payload.get("template_version", 1),
            "learned_at": payload.get("learned_at", ""),
            "examples": payload.get("examples", {}),
        }

        return {
            "tool_name": tool_name,
            "template_path": str(template_path),
            "learned": learned,
            "lifecycle_state": lifecycle_state,
            "template": payload,
        }

    def _learn_template(self, tool_name: str, analysis: ProjectAnalysis, tools_config: ToolsConfig) -> dict[str, object]:
        if tool_name != "crud_generator":
            return {
                "tool_name": tool_name,
                "strategy": "generic",
                "project_profile": tools_config.project_profile,
            }

        config = tools_config.tools.get("crud_generator", ToolEntry()).config
        examples = {
            "controller": self._find_example_file(config.get("controller_package", "")),
            "service": self._find_example_file(config.get("service_package", "")),
            "service_impl": self._find_example_file(f"{config.get('service_package', '')}.impl"),
            "mapper": self._find_example_file(config.get("mapper_package", "")),
            "domain": self._find_example_file(config.get("domain_package", "")),
            "mapper_xml": self._find_mapper_xml_example(analysis, tools_config),
        }
        return {
            "tool_name": tool_name,
            "strategy": "learned-from-project",
            "project_profile": tools_config.project_profile,
            "config_snapshot": config,
            "analysis_snapshot": analysis.to_dict(),
            "examples": examples,
        }

    def _find_example_file(self, package_name: str) -> str | None:
        if not package_name or package_name == "unknown":
            return None
        relative = Path(*package_name.split("."))
        matches = sorted(self.workspace.glob(f"**/{relative}/*.java"))
        if not matches:
            return None
        return str(matches[0])

    def _find_mapper_xml_example(self, analysis: ProjectAnalysis, tools_config: ToolsConfig) -> str | None:
        business_module = tools_config.project_profile.get("business_module", "")
        suffix = business_module.removeprefix("ruoyi-") if isinstance(business_module, str) else ""
        parts = ["mapper"]
        if suffix:
            parts.append(suffix)
        matches = sorted(self.workspace.glob(f"**/{Path(*parts)}/*Mapper.xml"))
        if not matches:
            matches = sorted(self.workspace.glob("**/*Mapper.xml"))
        return str(matches[0]) if matches else None
