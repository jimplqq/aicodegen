from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .configurator import WorkspaceConfigurator
from .detector import ProjectDetector
from .generator import CrudGenerator, FeaturePlanner
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

    def ensure_template(self, tool_name: str) -> dict[str, object]:
        self.storage.ensure()
        analysis = self.detector.detect()
        self.storage.save_analysis(analysis)
        tools_config = self._ensure_tools_config(analysis)
        result = self.template_manager.ensure_template(tool_name, analysis, tools_config)
        self.storage.save_tools_config(tools_config)
        return result

    def generate_feature(
        self,
        feature_name: str,
        *,
        entity_name: str | None = None,
        spec_data: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.storage.ensure()
        analysis = self.detector.detect()
        self.storage.save_analysis(analysis)
        tools_config = self._ensure_tools_config(analysis)
        template_result = self.template_manager.ensure_template("crud_generator", analysis, tools_config)
        self.storage.save_tools_config(tools_config)

        resolved_entity = self.feature_planner.infer_entity_name(feature_name, explicit_entity=entity_name)
        feature_spec = None if spec_data is None else FeatureSpec.from_dict(spec_data)
        generator = CrudGenerator(self.workspace, tools_config)
        entity_file = generator.generate_entity(resolved_entity, comment=feature_name, spec=feature_spec)
        generated = generator.generate(resolved_entity, comment=feature_name, spec=feature_spec)

        return {
            "workspace": str(self.workspace),
            "feature_name": feature_name,
            "entity_name": resolved_entity,
            "feature_spec": None if feature_spec is None else feature_spec.to_dict(),
            "template": template_result,
            "entity_file": {"kind": entity_file.kind, "path": str(entity_file.path)},
            "generated_files": [
                {"kind": item.kind, "path": str(item.path)}
                for item in generated
            ],
        }

    def _ensure_tools_config(self, analysis):
        tools_config = self.storage.load_tools_config()
        crud_tool = tools_config.tools.get("crud_generator")
        crud_module = ""
        if crud_tool is not None:
            crud_module = str(crud_tool.config.get("module_name", "") or "")
        needs_refresh = (
            not tools_config.tools
            or crud_tool is None
            or not crud_module
            or crud_module == "unknown"
        )
        if needs_refresh:
            rebuilt = self.configurator.build(analysis)
            rebuilt.enabled_tools = tools_config.enabled_tools
            if not rebuilt.suggested_tools:
                rebuilt.suggested_tools = tools_config.suggested_tools
            return rebuilt
        return tools_config

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
