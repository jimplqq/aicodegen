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
        try:
            if not template_path.exists():
                tool_entry.status = "learning"
                payload = self._learn_template(tool_name, analysis, tools_config)
                payload["template_version"] = 1
                payload["learned_at"] = datetime.now(UTC).isoformat()
                payload["lifecycle_state"] = "learned"
                learned = True
            else:
                payload = json.loads(template_path.read_text(encoding="utf-8"))

            if payload.get("lifecycle_state") == "failed":
                raise RuntimeError(str(payload.get("last_error", "Template is marked as failed.")))

            payload = self._verify_template(tool_name, payload, tools_config)
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            payload = {
                "tool_name": tool_name,
                "strategy": "failed",
                "project_profile": tools_config.project_profile,
                "lifecycle_state": "failed",
                "last_error": str(exc),
                "failed_at": datetime.now(UTC).isoformat(),
            }
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        lifecycle_state = str(payload.get("lifecycle_state", "learned"))
        tool_entry.status = lifecycle_state
        tool_entry.last_error = str(payload.get("last_error", ""))
        tool_entry.metadata = {
            "template_path": str(template_path),
            "strategy": payload.get("strategy", "generic"),
            "template_version": payload.get("template_version", 1),
            "learned_at": payload.get("learned_at", ""),
            "verified_at": payload.get("verified_at", ""),
            "examples": payload.get("examples", {}),
        }

        return {
            "tool_name": tool_name,
            "template_path": str(template_path),
            "learned": learned,
            "lifecycle_state": lifecycle_state,
            "is_error": lifecycle_state == "failed",
            "template": payload,
        }

    def mark_failed(
        self,
        tool_name: str,
        tools_config: ToolsConfig,
        error: str,
        *,
        details: dict[str, object] | None = None,
    ) -> dict[str, object]:
        template_path = self.storage.template_path(tool_name)
        payload: dict[str, object]
        if template_path.exists():
            payload = json.loads(template_path.read_text(encoding="utf-8"))
        else:
            payload = {"tool_name": tool_name, "strategy": "failed"}
        payload["lifecycle_state"] = "failed"
        payload["last_error"] = error
        payload["failed_at"] = datetime.now(UTC).isoformat()
        if details:
            payload["failure_details"] = details
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        tool_entry = tools_config.tools.setdefault(tool_name, ToolEntry())
        tool_entry.status = "failed"
        tool_entry.last_error = error
        tool_entry.metadata = {
            **tool_entry.metadata,
            "template_path": str(template_path),
            "failed_at": payload["failed_at"],
        }
        return {
            "tool_name": tool_name,
            "template_path": str(template_path),
            "learned": False,
            "lifecycle_state": "failed",
            "is_error": True,
            "template": payload,
        }

    def _verify_template(self, tool_name: str, payload: dict[str, object], tools_config: ToolsConfig) -> dict[str, object]:
        payload["lifecycle_state"] = "verifying"
        if tool_name == "crud_generator":
            self._verify_crud_template(tools_config)
        payload["lifecycle_state"] = "verified"
        payload["last_error"] = ""
        payload["verified_at"] = datetime.now(UTC).isoformat()
        return payload

    def _verify_crud_template(self, tools_config: ToolsConfig) -> None:
        tool = tools_config.tools.get("crud_generator")
        if tool is None:
            raise ValueError("crud_generator is not configured.")
        config = tool.config
        required = ["domain_package", "mapper_package", "service_package", "controller_package"]
        missing = [key for key in required if not str(config.get(key, "") or "") or str(config.get(key)) == "unknown"]
        if missing:
            raise ValueError(f"crud_generator template missing required config: {', '.join(missing)}")
        response_wrapper = str(config.get("response_wrapper", "AjaxResult") or "AjaxResult")
        if response_wrapper not in {"AjaxResult", "ResponseEntity", "ResultModel"}:
            raise ValueError(f"Unsupported response_wrapper: {response_wrapper}")
        module_name = str(config.get("module_name", "") or "")
        if module_name == "unknown":
            raise ValueError("crud_generator template has unresolved module_name.")

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
