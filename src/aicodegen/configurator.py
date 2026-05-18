from __future__ import annotations

from .models import ProjectAnalysis, ToolEntry, ToolsConfig


class WorkspaceConfigurator:
    def build(self, analysis: ProjectAnalysis) -> ToolsConfig:
        if analysis.language == "java" and analysis.architecture == "ruoyi":
            return self._build_ruoyi_java_config(analysis)
        if analysis.language == "java":
            return self._build_standard_java_config(analysis)
        return ToolsConfig(
            suggested_tools=["crud_generator"],
            project_profile={
                "language": analysis.language,
                "framework": analysis.framework,
            },
            tools={
                "crud_generator": ToolEntry(
                    status="not_initialized",
                    config={"mode": "generic"},
                )
            },
        )

    def _build_ruoyi_java_config(self, analysis: ProjectAnalysis) -> ToolsConfig:
        conventions = analysis.conventions
        business_module = conventions.get("business_module", "unknown")
        return ToolsConfig(
            suggested_tools=["crud_generator", "mybatis_mapper_generator", "vue_page_generator"],
            project_profile={
                "language": analysis.language,
                "framework": analysis.framework,
                "architecture": analysis.architecture,
                "build_tool": analysis.build_tool,
                "orm": analysis.orm,
                "base_package": analysis.base_package,
                "modules": analysis.modules,
                "business_module": business_module,
            },
            tools={
                "crud_generator": ToolEntry(
                    status="not_initialized",
                    config={
                        "template_profile": "ruoyi-mybatis",
                        "module_name": business_module,
                        "controller_package": conventions.get("controller_package"),
                        "service_package": conventions.get("service_package"),
                        "mapper_package": conventions.get("mapper_package"),
                        "domain_package": conventions.get("domain_package"),
                        "mapper_xml": conventions.get("mapper_xml", True),
                        "service_interface_prefix": conventions.get("service_interface_prefix", "I"),
                        "response_wrapper": conventions.get("response_wrapper", "AjaxResult"),
                        "controller_base_class": conventions.get("controller_base_class", "BaseController"),
                        "entity_base_class": conventions.get("entity_base_class", "BaseEntity"),
                    },
                )
            },
        )

    def _build_standard_java_config(self, analysis: ProjectAnalysis) -> ToolsConfig:
        return ToolsConfig(
            suggested_tools=["crud_generator"],
            project_profile={
                "language": analysis.language,
                "framework": analysis.framework,
                "build_tool": analysis.build_tool,
                "orm": analysis.orm,
                "base_package": analysis.base_package,
            },
            tools={
                "crud_generator": ToolEntry(
                    status="not_initialized",
                    config={
                        "template_profile": "spring-generic",
                        "base_package": analysis.base_package,
                        "orm": analysis.orm,
                    },
                )
            },
        )
