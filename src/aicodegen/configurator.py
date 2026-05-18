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
        project_root = str(conventions.get("project_root", "") or "")
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
                "project_root": project_root,
                "frontend_projects": list(conventions.get("frontend_projects", [])),
                "backend_projects": list(conventions.get("backend_projects", [])),
            },
            tools={
                "crud_generator": ToolEntry(
                    status="not_initialized",
                    config={
                        "template_profile": "ruoyi-mybatis",
                        "project_root": project_root,
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
        project_root = str(analysis.conventions.get("project_root", "") or "")
        base_package = analysis.base_package if analysis.base_package and analysis.base_package != "unknown" else "com.example"
        mapper_xml = analysis.orm in {"mybatis", "mybatis-plus"}
        return ToolsConfig(
            suggested_tools=["crud_generator"],
            project_profile={
                "language": analysis.language,
                "framework": analysis.framework,
                "build_tool": analysis.build_tool,
                "orm": analysis.orm,
                "base_package": base_package,
                "architecture": analysis.architecture,
                "modules": analysis.modules,
                "project_root": project_root,
                "frontend_projects": list(analysis.conventions.get("frontend_projects", [])),
                "backend_projects": list(analysis.conventions.get("backend_projects", [])),
            },
            tools={
                "crud_generator": ToolEntry(
                    status="not_initialized",
                    config={
                        "template_profile": "spring-generic",
                        "project_root": project_root,
                        "module_name": "",
                        "base_package": base_package,
                        "orm": analysis.orm,
                        "controller_package": f"{base_package}.controller",
                        "service_package": f"{base_package}.service",
                        "mapper_package": f"{base_package}.mapper",
                        "domain_package": f"{base_package}.domain",
                        "mapper_xml": mapper_xml,
                        "service_interface_prefix": "I",
                        "response_wrapper": "ResponseEntity",
                        "controller_base_class": "unknown",
                        "entity_base_class": "unknown",
                    },
                )
            },
        )
