from __future__ import annotations

import re
from pathlib import Path

from .models import ProjectAnalysis


class ProjectDetector:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def detect(self) -> ProjectAnalysis:
        if (self.workspace / "pom.xml").exists():
            return self._detect_java_maven()
        if (self.workspace / "build.gradle").exists() or (self.workspace / "build.gradle.kts").exists():
            return self._detect_gradle()
        if (self.workspace / "package.json").exists():
            return self._detect_node()
        if (self.workspace / "pyproject.toml").exists() or (self.workspace / "requirements.txt").exists():
            return self._detect_python()
        if (self.workspace / "go.mod").exists():
            return self._detect_go()
        return ProjectAnalysis()

    def _detect_java_maven(self) -> ProjectAnalysis:
        pom = (self.workspace / "pom.xml").read_text(encoding="utf-8", errors="ignore")
        modules = self._find_maven_modules(pom)
        package_candidates = self._find_java_package_candidates()
        base_package = self._derive_base_package(package_candidates)
        has_mapper_xml = bool(list(self.workspace.glob("**/*Mapper.xml")))
        has_ruoyi = "ruoyi" in pom.lower() or any(module.startswith("ruoyi-") for module in modules)
        framework = "spring-boot" if "spring-boot" in pom else "java"
        architecture = "ruoyi" if has_ruoyi else "multi-module" if modules else "standard"
        test_framework = self._detect_java_test_framework(pom)
        java_version = self._extract_first_match(
            pom,
            [
                r"<maven\.compiler\.source>\s*([^<\s]+)\s*</maven\.compiler\.source>",
                r"<java\.version>\s*([^<\s]+)\s*</java\.version>",
                r"<maven\.compiler\.target>\s*([^<\s]+)\s*</maven\.compiler\.target>",
            ],
        )
        spring_boot_version = self._extract_first_match(
            pom,
            [
                r"<parent>.*?<artifactId>\s*spring-boot-starter-parent\s*</artifactId>.*?<version>\s*([^<\s]+)\s*</version>.*?</parent>",
                r"<spring-boot\.version>\s*([^<\s]+)\s*</spring-boot\.version>",
            ],
            flags=re.DOTALL,
        )
        orm = self._detect_java_orm(pom, has_mapper_xml=has_mapper_xml)
        libraries = {
            "lombok": "lombok" in pom,
            "mapstruct": "mapstruct" in pom,
            "openapi": "springdoc-openapi" in pom or "swagger" in pom,
            "mybatis": "mybatis" in pom or has_mapper_xml,
            "mybatis_plus": "mybatis-plus" in pom,
            "jpa": "spring-boot-starter-data-jpa" in pom or "<artifactId>hibernate-core</artifactId>" in pom,
        }
        conventions = self._build_java_conventions(
            architecture=architecture,
            base_package=base_package,
            modules=modules,
            has_mapper_xml=has_mapper_xml,
        )
        return ProjectAnalysis(
            language="java",
            build_tool="maven",
            framework=framework,
            package_manager="maven",
            test_framework=test_framework,
            java_version=java_version,
            spring_boot_version=spring_boot_version,
            orm=orm,
            architecture=architecture,
            modules=modules,
            base_package=base_package,
            libraries=libraries,
            conventions=conventions,
            hints={
                "descriptor": "pom.xml",
                "has_mapper_xml": has_mapper_xml,
            },
        )

    def _detect_gradle(self) -> ProjectAnalysis:
        build_file = self.workspace / "build.gradle"
        if not build_file.exists():
            build_file = self.workspace / "build.gradle.kts"
        content = build_file.read_text(encoding="utf-8", errors="ignore")
        framework = "spring-boot" if "spring-boot" in content else "java"
        orm = "mybatis-plus" if "mybatis-plus" in content else "mybatis" if "mybatis" in content else "jpa" if "data-jpa" in content else "unknown"
        libraries = {
            "lombok": "lombok" in content,
            "mapstruct": "mapstruct" in content,
            "openapi": "springdoc-openapi" in content or "swagger" in content,
            "mybatis": "mybatis" in content,
            "mybatis_plus": "mybatis-plus" in content,
            "jpa": "data-jpa" in content,
        }
        return ProjectAnalysis(
            language="java",
            build_tool="gradle",
            framework=framework,
            package_manager="gradle",
            test_framework="junit5" if "junit-jupiter" in content else "junit" if "junit" in content else "unknown",
            java_version=self._extract_first_match(
                content,
                [
                    r"sourceCompatibility\s*=\s*['\"]?([^'\"\s]+)",
                    r"JavaVersion\.VERSION_([0-9_]+)",
                ],
            ).replace("_", "."),
            spring_boot_version=self._extract_first_match(
                content,
                [
                    r"id\s+['\"]org\.springframework\.boot['\"]\s+version\s+['\"]([^'\"]+)['\"]",
                ],
            ),
            orm=orm,
            libraries=libraries,
            hints={"descriptor": build_file.name},
        )

    def _detect_node(self) -> ProjectAnalysis:
        package_json = (self.workspace / "package.json").read_text(encoding="utf-8", errors="ignore")
        framework = "node"
        if "\"next\"" in package_json:
            framework = "nextjs"
        elif "\"react\"" in package_json:
            framework = "react"
        elif "\"express\"" in package_json:
            framework = "express"
        test_framework = "vitest" if "\"vitest\"" in package_json else "jest" if "\"jest\"" in package_json else "unknown"
        return ProjectAnalysis(
            language="typescript" if "\"typescript\"" in package_json else "javascript",
            build_tool="node",
            framework=framework,
            package_manager="npm",
            test_framework=test_framework,
            hints={"descriptor": "package.json"},
        )

    def _detect_python(self) -> ProjectAnalysis:
        pyproject = self.workspace / "pyproject.toml"
        requirements = self.workspace / "requirements.txt"
        content = ""
        descriptor = "requirements.txt"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            descriptor = "pyproject.toml"
        elif requirements.exists():
            content = requirements.read_text(encoding="utf-8", errors="ignore")
        framework = "python"
        lowered = content.lower()
        if "fastapi" in lowered:
            framework = "fastapi"
        elif "django" in lowered:
            framework = "django"
        elif "flask" in lowered:
            framework = "flask"
        test_framework = "pytest" if "pytest" in lowered else "unittest"
        return ProjectAnalysis(
            language="python",
            build_tool="python",
            framework=framework,
            package_manager="pip",
            test_framework=test_framework,
            hints={"descriptor": descriptor},
        )

    def _detect_go(self) -> ProjectAnalysis:
        go_mod = (self.workspace / "go.mod").read_text(encoding="utf-8", errors="ignore")
        framework = "go"
        if "gin-gonic/gin" in go_mod:
            framework = "gin"
        return ProjectAnalysis(
            language="go",
            build_tool="go",
            framework=framework,
            package_manager="go",
            test_framework="go test",
            hints={"descriptor": "go.mod"},
        )

    def _detect_java_test_framework(self, content: str) -> str:
        if "spring-boot-starter-test" in content or "junit-jupiter" in content:
            return "junit5"
        if re.search(r"<artifactId>\s*junit\s*</artifactId>", content):
            return "junit4"
        if "testng" in content:
            return "testng"
        return "unknown"

    def _detect_java_orm(self, content: str, *, has_mapper_xml: bool = False) -> str:
        if "mybatis-plus" in content:
            return "mybatis-plus"
        if "mybatis" in content or has_mapper_xml:
            return "mybatis"
        if "spring-boot-starter-data-jpa" in content or "<artifactId>hibernate-core</artifactId>" in content:
            return "jpa"
        return "unknown"

    def _find_maven_modules(self, pom: str) -> list[str]:
        return re.findall(r"<module>\s*([^<\s]+)\s*</module>", pom)

    def _find_java_package_candidates(self) -> list[str]:
        packages: set[str] = set()
        for java_file in self.workspace.glob("**/*.java"):
            if len(packages) >= 20:
                break
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            match = re.search(r"package\s+([a-zA-Z0-9_.]+);", content)
            if match:
                packages.add(match.group(1))
        return sorted(packages)

    def _build_java_conventions(
        self,
        *,
        architecture: str,
        base_package: str,
        modules: list[str],
        has_mapper_xml: bool,
    ) -> dict[str, object]:
        controller_package = "unknown"
        service_package = "unknown"
        mapper_package = "unknown"
        domain_package = "unknown"
        admin_module = next((m for m in modules if m.endswith("admin")), modules[0] if modules else "")
        business_module = next((m for m in modules if m.endswith("-em")), "")
        business_suffix = business_module.removeprefix("ruoyi-") if business_module else ""
        if architecture == "ruoyi" and base_package.startswith("com.ruoyi"):
            controller_package = f"com.ruoyi.{business_suffix}.controller" if business_module else "com.ruoyi.web.controller"
            if business_module:
                service_package = f"com.ruoyi.{business_suffix}.service"
                mapper_package = f"com.ruoyi.{business_suffix}.mapper"
                domain_package = f"com.ruoyi.{business_suffix}.domain"
        return {
            "multi_module": bool(modules),
            "modules": modules,
            "admin_module": admin_module or "unknown",
            "business_module": business_module or "unknown",
            "ui_module": next((m for m in modules if m.endswith("ui")), "unknown"),
            "controller_package": controller_package,
            "service_package": service_package,
            "mapper_package": mapper_package,
            "domain_package": domain_package,
            "mapper_xml": has_mapper_xml,
            "service_interface_prefix": "I",
            "response_wrapper": "AjaxResult" if architecture == "ruoyi" else "unknown",
            "controller_base_class": "BaseController" if architecture == "ruoyi" else "unknown",
            "entity_base_class": "BaseEntity" if architecture == "ruoyi" else "unknown",
        }

    def _extract_first_match(
        self,
        content: str,
        patterns: list[str],
        *,
        flags: int = 0,
    ) -> str:
        for pattern in patterns:
            match = re.search(pattern, content, flags)
            if match:
                return match.group(1).strip()
        return "unknown"

    def _derive_base_package(self, package_candidates: list[str]) -> str:
        if not package_candidates:
            return "unknown"
        split_candidates = [candidate.split(".") for candidate in package_candidates if candidate]
        if not split_candidates:
            return "unknown"
        prefix: list[str] = []
        for parts in zip(*split_candidates):
            if len(set(parts)) == 1:
                prefix.append(parts[0])
            else:
                break
        if len(prefix) >= 2:
            return ".".join(prefix)
        shortest = min(split_candidates, key=len)
        return ".".join(shortest[:2]) if len(shortest) >= 2 else shortest[0]
