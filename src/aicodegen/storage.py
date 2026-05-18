from __future__ import annotations

from pathlib import Path
import json

from .models import ProjectAnalysis, ToolsConfig, WorkspaceConfig


class WorkspaceStorage:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.agent_dir = workspace / ".agent"
        self.tools_path = self.agent_dir / "tools.json"
        self.analysis_path = self.agent_dir / "project_analysis.json"
        self.workspace_config_path = self.agent_dir / "workspace_config.json"

    def ensure(self) -> None:
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        (self.agent_dir / "tools").mkdir(parents=True, exist_ok=True)
        if not self.workspace_config_path.exists():
            self.save_workspace_config(WorkspaceConfig())
        self.template_root().mkdir(parents=True, exist_ok=True)
        if not self.tools_path.exists():
            self.save_tools_config(ToolsConfig())

    def load_tools_config(self) -> ToolsConfig:
        return ToolsConfig.from_path(self.tools_path)

    def save_tools_config(self, config: ToolsConfig) -> None:
        self.tools_path.write_text(
            json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_workspace_config(self) -> WorkspaceConfig:
        return WorkspaceConfig.from_path(self.workspace_config_path)

    def save_workspace_config(self, config: WorkspaceConfig) -> None:
        config.write_to(self.workspace_config_path)

    def save_analysis(self, analysis: ProjectAnalysis) -> None:
        analysis.write_to(self.analysis_path)

    def template_root(self) -> Path:
        config = self.load_workspace_config()
        root = Path(config.template_root or ".agent/templates")
        if not root.is_absolute():
            root = self.workspace / root
        return root

    def template_path(self, template_name: str) -> Path:
        return self.template_root() / f"{template_name}.json"
