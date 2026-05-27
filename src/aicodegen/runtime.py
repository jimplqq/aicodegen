from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import subprocess
from typing import Any

from .configurator import WorkspaceConfigurator
from .detector import ProjectDetector
from .generator import CrudGenerator, FeaturePlanner, SqlSpecParser
from .models import FeatureSpec, WorkspaceConfig
from .path_setup import PathSetupService
from .storage import WorkspaceStorage
from .template_manager import TemplateManager


class RuntimeService:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.storage = WorkspaceStorage(workspace)
        self.detector = ProjectDetector(workspace)
        self.configurator = WorkspaceConfigurator()
        self.template_manager = TemplateManager(workspace, self.storage)
        self.feature_planner = FeaturePlanner()
        self.sql_spec_parser = SqlSpecParser()
        self.path_setup = PathSetupService(workspace)

    def init_workspace(
        self,
        *,
        language: str | None = None,
        framework: str | None = None,
        template_root: str | None = None,
        build_command: str | None = None,
        test_command: str | None = None,
        force: bool = False,
    ) -> dict:
        self.storage.ensure()
        analysis = self.detector.detect()
        self.storage.save_analysis(analysis)
        tools_config = self.configurator.build(analysis)
        self.storage.save_tools_config(tools_config)
        workspace_config = self._build_workspace_config(
            analysis,
            language=language,
            framework=framework,
            template_root=template_root,
            build_command=build_command,
            test_command=test_command,
            force=force,
        )
        self.storage.save_workspace_config(workspace_config)
        self.storage.template_root().mkdir(parents=True, exist_ok=True)
        path_setup = self.path_setup.ensure_cli_on_user_path()
        return {
            "workspace": str(self.workspace),
            "agent_dir": str(self.storage.agent_dir),
            "tools_path": str(self.storage.tools_path),
            "analysis_path": str(self.storage.analysis_path),
            "workspace_config_path": str(self.storage.workspace_config_path),
            "template_root": str(self.storage.template_root()),
            "project_profile": tools_config.project_profile,
            "suggested_tools": tools_config.suggested_tools,
            "detected": {
                "language": analysis.language,
                "framework": analysis.framework,
                "build_tool": analysis.build_tool,
                "test_framework": analysis.test_framework,
            },
            "configured": workspace_config.to_dict(),
            "path_setup": path_setup,
        }

    def detect_workspace(self) -> dict:
        self.storage.ensure()
        analysis = self.detector.detect()
        self.storage.save_analysis(analysis)
        existing_config = self.storage.load_tools_config()
        refreshed = self.configurator.build(analysis)
        refreshed.enabled_tools = existing_config.enabled_tools
        self.storage.save_tools_config(refreshed)
        return asdict(analysis)

    def status(self) -> dict:
        tools_config = self.storage.load_tools_config()
        workspace_config = self.storage.load_workspace_config()
        return {
            "workspace": str(self.workspace),
            "initialized": self.storage.agent_dir.exists(),
            "tools_config": str(self.storage.tools_path),
            "analysis": str(self.storage.analysis_path),
            "workspace_config": str(self.storage.workspace_config_path),
            "template_root": str(self.storage.template_root()),
            "configured": workspace_config.to_dict(),
            "project_profile": tools_config.project_profile,
            "suggested_tools": tools_config.suggested_tools,
            "tools": {
                name: {
                    "status": entry.status,
                    "last_error": entry.last_error,
                    "metadata": entry.metadata,
                }
                for name, entry in tools_config.tools.items()
            },
        }

    def doctor(self) -> dict[str, object]:
        checks: list[dict[str, object]] = []
        initialized = self.storage.agent_dir.exists()
        checks.append(
            {
                "code": "workspace_initialized" if initialized else "workspace_not_initialized",
                "ok": initialized,
                "message": ".agent workspace state exists." if initialized else "Run `aicodegen init` before generation.",
            }
        )
        analysis = self.detector.detect()
        checks.append(
            {
                "code": "project_detected" if analysis.language != "unknown" else "project_unknown",
                "ok": analysis.language != "unknown",
                "message": f"Detected {analysis.language}/{analysis.framework}.",
            }
        )
        tools_config = self.storage.load_tools_config() if self.storage.tools_path.exists() else self.configurator.build(analysis)
        crud_tool = tools_config.tools.get("crud_generator")
        template_path = self.storage.template_path("crud_generator") if initialized else self.workspace / ".agent" / "templates" / "crud_generator.json"
        template_state = "missing"
        template_ok = False
        last_error = ""
        if template_path.exists():
            import json

            payload = json.loads(template_path.read_text(encoding="utf-8"))
            template_state = str(payload.get("lifecycle_state", "unknown"))
            last_error = str(payload.get("last_error", ""))
            template_ok = template_state == "verified"
            validation = payload.get("failure_details", {})
        elif crud_tool is not None and crud_tool.status in {"verified", "learned"}:
            template_state = crud_tool.status
            template_ok = crud_tool.status == "verified"
            last_error = crud_tool.last_error
            validation = {}
        else:
            validation = {}
        checks.append(
            {
                "code": "template_verified" if template_ok else "template_not_verified",
                "ok": True,
                "message": f"crud_generator template state: {template_state}",
                "last_error": last_error,
                "severity": "info" if template_ok else "warning",
                "details": validation,
            }
        )
        ready = all(bool(item["ok"]) for item in checks)
        return {
            "workspace": str(self.workspace),
            "ready": ready,
            "detected": analysis.to_dict(),
            "checks": checks,
        }

    def ensure_template(self, tool_name: str) -> dict[str, object]:
        self.storage.ensure()
        analysis = self.detector.detect()
        self.storage.save_analysis(analysis)
        tools_config = self._ensure_tools_config(analysis)
        result = self.template_manager.ensure_template(tool_name, analysis, tools_config)
        validation = self._run_validation_commands(self.storage.load_workspace_config())
        result["validation"] = validation
        if not validation["ok"]:
            result = self.template_manager.mark_failed(
                tool_name,
                tools_config,
                str(validation["last_error"]),
                details={"validation": validation},
            )
        self.storage.save_tools_config(tools_config)
        return result

    def generate_feature(
        self,
        feature_name: str,
        *,
        entity_name: str | None = None,
        spec_data: dict[str, object] | None = None,
        sql: str | None = None,
    ) -> dict[str, object]:
        self.storage.ensure()
        analysis = self.detector.detect()
        self.storage.save_analysis(analysis)
        tools_config = self._ensure_tools_config(analysis)
        template_result = self.template_manager.ensure_template("crud_generator", analysis, tools_config)
        self.storage.save_tools_config(tools_config)
        self._raise_if_template_failed(template_result)

        feature_spec = None
        source = "name"
        if sql:
            feature_spec = self.sql_spec_parser.parse(sql, fallback_name=feature_name)
            source = "sql"
        elif spec_data is not None:
            feature_spec = FeatureSpec.from_dict(spec_data)
            source = "spec"
        resolved_entity = entity_name or (feature_spec.entity if feature_spec is not None else "")
        resolved_entity = self.feature_planner.infer_entity_name(feature_name, explicit_entity=resolved_entity or None)
        generator = CrudGenerator(self.workspace, tools_config)
        entity_file = generator.generate_entity(resolved_entity, comment=feature_name, spec=feature_spec)
        generated = generator.generate(resolved_entity, comment=feature_name, spec=feature_spec)
        validation = self._run_validation_commands(self.storage.load_workspace_config())
        if not validation["ok"]:
            failed_result = self.template_manager.mark_failed(
                "crud_generator",
                tools_config,
                str(validation["last_error"]),
                details={"validation": validation},
            )
            self.storage.save_tools_config(tools_config)
            self._raise_if_template_failed(failed_result)

        return {
            "workspace": str(self.workspace),
            "feature_name": feature_name,
            "entity_name": resolved_entity,
            "source": source,
            "feature_spec": None if feature_spec is None else feature_spec.to_dict(),
            "template": template_result,
            "entity_file": {"kind": entity_file.kind, "path": str(entity_file.path)},
            "generated_files": [
                {"kind": item.kind, "path": str(item.path)}
                for item in generated
            ],
            "validation": validation,
        }

    def prepare_tools_config_for_generation(self) -> object:
        self.storage.ensure()
        analysis = self.detector.detect()
        self.storage.save_analysis(analysis)
        tools_config = self._ensure_tools_config(analysis)
        self.storage.save_tools_config(tools_config)
        return tools_config

    def _raise_if_template_failed(self, result: dict[str, object]) -> None:
        if result.get("lifecycle_state") == "failed":
            template = result.get("template", {})
            last_error = ""
            if isinstance(template, dict):
                last_error = str(template.get("last_error", ""))
            raise RuntimeError(last_error or "Template preparation failed.")

    def _run_validation_commands(self, workspace_config: WorkspaceConfig) -> dict[str, object]:
        commands: list[tuple[str, str]] = []
        build_command = workspace_config.script_commands.get("build", "").strip()
        test_command = workspace_config.validation_commands.get("test", "").strip()
        if build_command:
            commands.append(("build", build_command))
        if test_command:
            commands.append(("test", test_command))
        results: list[dict[str, object]] = []
        for name, command in commands:
            result = self._run_workspace_command(name, command)
            results.append(result)
            if not result["ok"]:
                return {
                    "ok": False,
                    "commands": results,
                    "last_error": f"{name} command failed with exit code {result['exit_code']}: {command}",
                }
        return {"ok": True, "commands": results, "last_error": ""}

    def _run_workspace_command(self, name: str, command: str) -> dict[str, object]:
        completed = subprocess.run(
            command,
            cwd=self.workspace,
            shell=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        return {
            "name": name,
            "command": command,
            "exit_code": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }

    def _ensure_tools_config(self, analysis):
        tools_config = self.storage.load_tools_config()
        crud_tool = tools_config.tools.get("crud_generator")
        crud_module = ""
        template_profile = ""
        if crud_tool is not None:
            crud_module = str(crud_tool.config.get("module_name", "") or "")
            template_profile = str(crud_tool.config.get("template_profile", "") or "")
        requires_explicit_module = template_profile == "ruoyi-mybatis" or analysis.architecture == "ruoyi"
        needs_refresh = (
            not tools_config.tools
            or crud_tool is None
            or (requires_explicit_module and (not crud_module or crud_module == "unknown"))
        )
        if needs_refresh:
            rebuilt = self.configurator.build(analysis)
            rebuilt.enabled_tools = tools_config.enabled_tools
            if not rebuilt.suggested_tools:
                rebuilt.suggested_tools = tools_config.suggested_tools
            return rebuilt
        rebuilt = self.configurator.build(analysis)
        rebuilt.enabled_tools = tools_config.enabled_tools
        if not rebuilt.suggested_tools:
            rebuilt.suggested_tools = tools_config.suggested_tools
        return self._merge_missing_tool_defaults(tools_config, rebuilt)
        return tools_config

    def _merge_missing_tool_defaults(self, current, rebuilt):
        current.project_profile = {**rebuilt.project_profile, **current.project_profile}
        current.suggested_tools = current.suggested_tools or rebuilt.suggested_tools
        for name, rebuilt_entry in rebuilt.tools.items():
            current_entry = current.tools.get(name)
            if current_entry is None:
                current.tools[name] = rebuilt_entry
                continue
            current_entry.config = {**rebuilt_entry.config, **current_entry.config}
        return current

    def _build_workspace_config(
        self,
        analysis,
        *,
        language: str | None,
        framework: str | None,
        template_root: str | None,
        build_command: str | None,
        test_command: str | None,
        force: bool,
    ) -> WorkspaceConfig:
        existing = self.storage.load_workspace_config()
        config = WorkspaceConfig() if force else existing

        resolved_language = (language or config.language or analysis.language).strip()
        resolved_framework = (framework or config.framework or analysis.framework).strip()
        resolved_template_root = (template_root or config.template_root or ".agent/templates").strip()

        script_commands = dict(config.script_commands)
        validation_commands = dict(config.validation_commands)
        if build_command:
            script_commands["build"] = build_command.strip()
        if test_command:
            validation_commands["test"] = test_command.strip()

        stack_overrides = dict(config.stack_overrides)
        if language:
            stack_overrides["language"] = resolved_language
        if framework:
            stack_overrides["framework"] = resolved_framework

        generation_defaults = dict(config.generation_defaults)
        generation_defaults.setdefault("workspace", str(self.workspace))

        agent_integration = dict(config.agent_integration)
        agent_integration.setdefault("mcp_command", "aicodegen mcp")

        return WorkspaceConfig(
            language=resolved_language,
            framework=resolved_framework,
            template_root=resolved_template_root,
            stack_overrides=stack_overrides,
            script_commands=script_commands,
            validation_commands=validation_commands,
            generation_defaults=generation_defaults,
            agent_integration=agent_integration,
        )
