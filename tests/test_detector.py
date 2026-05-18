from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from aicodegen.configurator import WorkspaceConfigurator
from aicodegen.detector import ProjectDetector
from aicodegen.generator import CrudGenerator, FeaturePlanner
from aicodegen.mcp_server import McpServer
from aicodegen.path_setup import merge_windows_path_entries
from aicodegen.runtime import RuntimeService


class DetectorTests(unittest.TestCase):
    def test_detects_maven_spring_boot(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <parent>
                    <groupId>org.springframework.boot</groupId>
                    <artifactId>spring-boot-starter-parent</artifactId>
                    <version>3.2.5</version>
                  </parent>
                  <properties>
                    <java.version>17</java.version>
                  </properties>
                  <dependencies>
                    <dependency>
                      <groupId>org.springframework.boot</groupId>
                      <artifactId>spring-boot-starter-web</artifactId>
                    </dependency>
                    <dependency>
                      <groupId>org.springframework.boot</groupId>
                      <artifactId>spring-boot-starter-test</artifactId>
                    </dependency>
                  </dependencies>
                </project>
                """,
                encoding="utf-8",
            )
            analysis = ProjectDetector(workspace).detect()
            self.assertEqual(analysis.language, "java")
            self.assertEqual(analysis.build_tool, "maven")
            self.assertEqual(analysis.framework, "spring-boot")
            self.assertEqual(analysis.java_version, "17")
            self.assertEqual(analysis.spring_boot_version, "3.2.5")
            self.assertEqual(analysis.test_framework, "junit5")

    def test_detects_java_orm_and_libraries(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <properties>
                    <maven.compiler.source>21</maven.compiler.source>
                  </properties>
                  <dependencies>
                    <dependency>
                      <groupId>com.baomidou</groupId>
                      <artifactId>mybatis-plus-boot-starter</artifactId>
                    </dependency>
                    <dependency>
                      <groupId>org.projectlombok</groupId>
                      <artifactId>lombok</artifactId>
                    </dependency>
                    <dependency>
                      <groupId>org.mapstruct</groupId>
                      <artifactId>mapstruct</artifactId>
                    </dependency>
                    <dependency>
                      <groupId>org.springdoc</groupId>
                      <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
                    </dependency>
                    <dependency>
                      <groupId>org.junit.jupiter</groupId>
                      <artifactId>junit-jupiter</artifactId>
                    </dependency>
                  </dependencies>
                </project>
                """,
                encoding="utf-8",
            )
            analysis = ProjectDetector(workspace).detect()
            self.assertEqual(analysis.orm, "mybatis-plus")
            self.assertEqual(analysis.java_version, "21")
            self.assertEqual(analysis.test_framework, "junit5")
            self.assertTrue(analysis.libraries["lombok"])
            self.assertTrue(analysis.libraries["mapstruct"])
            self.assertTrue(analysis.libraries["openapi"])

    def test_detects_ruoyi_and_generates_default_config(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <modules>
                    <module>ruoyi-admin</module>
                    <module>ruoyi-common</module>
                    <module>ruoyi-em</module>
                    <module>ruoyi-ui</module>
                  </modules>
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "DemoController.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.ruoyi.em.controller;\npublic class DemoController {}\n",
                encoding="utf-8",
            )
            mapper_xml = workspace / "ruoyi-em" / "src" / "main" / "resources" / "mapper" / "em" / "DemoMapper.xml"
            mapper_xml.parent.mkdir(parents=True, exist_ok=True)
            mapper_xml.write_text("<mapper></mapper>", encoding="utf-8")
            analysis = ProjectDetector(workspace).detect()
            self.assertEqual(analysis.architecture, "ruoyi")
            self.assertEqual(analysis.orm, "mybatis")
            self.assertIn("ruoyi-em", analysis.modules)
            config = WorkspaceConfigurator().build(analysis)
            self.assertIn("crud_generator", config.tools)
            self.assertEqual(config.tools["crud_generator"].config["template_profile"], "ruoyi-mybatis")
            self.assertEqual(config.project_profile["business_module"], "ruoyi-em")
            self.assertEqual(config.tools["crud_generator"].config["controller_package"], "com.ruoyi.em.controller")

    def test_generates_ruoyi_crud_files(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <modules>
                    <module>ruoyi-admin</module>
                    <module>ruoyi-em</module>
                  </modules>
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "DemoController.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.ruoyi.em.controller;\npublic class DemoController {}\n",
                encoding="utf-8",
            )
            mapper_xml = workspace / "ruoyi-em" / "src" / "main" / "resources" / "mapper" / "em" / "DemoMapper.xml"
            mapper_xml.parent.mkdir(parents=True, exist_ok=True)
            mapper_xml.write_text("<mapper></mapper>", encoding="utf-8")
            analysis = ProjectDetector(workspace).detect()
            tools_config = WorkspaceConfigurator().build(analysis)
            generated = CrudGenerator(workspace, tools_config).generate("LampPlan", comment="灯具方案")
            generated_paths = {item.kind: item.path for item in generated}
            self.assertTrue(generated_paths["domain"].exists())
            self.assertTrue(generated_paths["controller"].exists())
            controller_content = generated_paths["controller"].read_text(encoding="utf-8")
            self.assertIn("package com.ruoyi.em.controller;", controller_content)
            self.assertIn("@RequestMapping(\"/lamp-plan\")", controller_content)
            mapper_xml_content = generated_paths["mapper_xml"].read_text(encoding="utf-8")
            self.assertIn("namespace=\"com.ruoyi.em.mapper.LampPlanMapper\"", mapper_xml_content)

    def test_ensure_template_learns_from_project_examples(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <modules>
                    <module>ruoyi-admin</module>
                    <module>ruoyi-em</module>
                  </modules>
                </project>
                """,
                encoding="utf-8",
            )
            files = {
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "SampleController.java":
                    "package com.ruoyi.em.controller;\npublic class SampleController {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "service" / "ISampleService.java":
                    "package com.ruoyi.em.service;\npublic interface ISampleService {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "service" / "impl" / "SampleServiceImpl.java":
                    "package com.ruoyi.em.service.impl;\npublic class SampleServiceImpl {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "mapper" / "SampleMapper.java":
                    "package com.ruoyi.em.mapper;\npublic interface SampleMapper {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "domain" / "Sample.java":
                    "package com.ruoyi.em.domain;\npublic class Sample {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "resources" / "mapper" / "em" / "SampleMapper.xml":
                    "<mapper></mapper>",
            }
            for path, content in files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            service = RuntimeService(workspace)
            service.init_workspace()
            result = service.ensure_template("crud_generator")
            self.assertIn("template_path", result)
            self.assertTrue(Path(result["template_path"]).exists())
            self.assertEqual(result["lifecycle_state"], "learned")
            self.assertEqual(result["template"]["strategy"], "learned-from-project")
            self.assertEqual(result["template"]["template_version"], 1)
            self.assertIn("learned_at", result["template"])
            self.assertIn("SampleController.java", result["template"]["examples"]["controller"])
            status = service.status()
            self.assertEqual(status["tools"]["crud_generator"]["status"], "learned")
            self.assertEqual(status["tools"]["crud_generator"]["metadata"]["template_version"], 1)

    def test_generates_entity_only_file(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <modules>
                    <module>ruoyi-em</module>
                  </modules>
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "DemoController.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.ruoyi.em.controller;\npublic class DemoController {}\n",
                encoding="utf-8",
            )
            service = RuntimeService(workspace)
            service.init_workspace()
            tools_config = service.storage.load_tools_config()
            generated = CrudGenerator(workspace, tools_config).generate_entity("DeviceLedger", comment="设备台账")
            self.assertTrue(generated.path.exists())
            content = generated.path.read_text(encoding="utf-8")
            self.assertIn("class DeviceLedger", content)
            self.assertIn("设备台账对象 DeviceLedger", content)

    def test_feature_planner_infers_entity_name(self) -> None:
        planner = FeaturePlanner()
        self.assertEqual(planner.infer_entity_name("设备台账"), "DeviceLedger")
        self.assertEqual(planner.infer_entity_name("lamp plan"), "LampPlan")
        self.assertEqual(planner.infer_entity_name("用户管理", explicit_entity="UserAccount"), "UserAccount")

    def test_runtime_generates_feature_scaffold(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <modules>
                    <module>ruoyi-admin</module>
                    <module>ruoyi-em</module>
                  </modules>
                </project>
                """,
                encoding="utf-8",
            )
            files = {
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "SampleController.java":
                    "package com.ruoyi.em.controller;\npublic class SampleController {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "service" / "ISampleService.java":
                    "package com.ruoyi.em.service;\npublic interface ISampleService {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "service" / "impl" / "SampleServiceImpl.java":
                    "package com.ruoyi.em.service.impl;\npublic class SampleServiceImpl {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "mapper" / "SampleMapper.java":
                    "package com.ruoyi.em.mapper;\npublic interface SampleMapper {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "domain" / "Sample.java":
                    "package com.ruoyi.em.domain;\npublic class Sample {}\n",
                workspace / "ruoyi-em" / "src" / "main" / "resources" / "mapper" / "em" / "SampleMapper.xml":
                    "<mapper></mapper>",
            }
            for path, content in files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            service = RuntimeService(workspace)
            service.init_workspace()
            result = service.generate_feature("设备台账")
            self.assertEqual(result["entity_name"], "DeviceLedger")
            self.assertTrue(Path(result["entity_file"]["path"]).exists())
            generated_kinds = {item["kind"] for item in result["generated_files"]}
            self.assertIn("controller", generated_kinds)
            self.assertIn("mapper_xml", generated_kinds)

    def test_runtime_feature_generation_recovers_from_empty_tool_config(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <modules>
                    <module>ruoyi-admin</module>
                    <module>ruoyi-em</module>
                  </modules>
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "DemoController.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.ruoyi.em.controller;\npublic class DemoController {}\n",
                encoding="utf-8",
            )
            service = RuntimeService(workspace)
            service.storage.ensure()
            service.storage.tools_path.write_text(
                '{"enabled_tools":[],"tools":{}}',
                encoding="utf-8",
            )
            result = service.generate_feature("设备台账")
            self.assertEqual(result["entity_name"], "DeviceLedger")
            self.assertTrue(Path(result["entity_file"]["path"]).exists())

    def test_mcp_server_exposes_generate_feature_tool(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <modules>
                    <module>ruoyi-admin</module>
                    <module>ruoyi-em</module>
                  </modules>
                </project>
                """,
                encoding="utf-8",
            )
            sample = workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "SampleController.java"
            sample.parent.mkdir(parents=True, exist_ok=True)
            sample.write_text("package com.ruoyi.em.controller;\npublic class SampleController {}\n", encoding="utf-8")
            server = McpServer(workspace)
            tool_list = server._handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            names = {tool["name"] for tool in tool_list["result"]["tools"]}
            self.assertIn("generate_feature", names)
            call_result = server._handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "generate_feature",
                        "arguments": {"name": "设备台账"},
                    },
                }
            )
            self.assertFalse(call_result["result"]["isError"])
            structured = call_result["result"]["structuredContent"]
            self.assertEqual(structured["entity_name"], "DeviceLedger")

    def test_merge_windows_path_entries_adds_new_value_once(self) -> None:
        merged, changed = merge_windows_path_entries(
            r"C:\Windows\System32;C:\Tools",
            r"C:\workspace\java_workspace\emlight\.venv\Scripts",
        )
        self.assertTrue(changed)
        self.assertTrue(merged.startswith(r"C:\workspace\java_workspace\emlight\.venv\Scripts;"))

        merged_again, changed_again = merge_windows_path_entries(
            merged,
            r"C:\workspace\java_workspace\emlight\.venv\Scripts",
        )
        self.assertFalse(changed_again)
        self.assertEqual(merged_again, merged)

    def test_init_workspace_reports_path_setup(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text("<project></project>", encoding="utf-8")
            service = RuntimeService(workspace)
            service.path_setup.ensure_cli_on_user_path = lambda: {  # type: ignore[method-assign]
                "status": "added",
                "path_added": True,
                "target": r"C:\demo\.venv\Scripts",
            }
            result = service.init_workspace()
            self.assertIn("path_setup", result)
            self.assertEqual(result["path_setup"]["status"], "added")
            self.assertIn("workspace_config_path", result)
            self.assertEqual(result["template_root"], str(workspace / ".agent" / "templates"))
            config = service.storage.load_workspace_config()
            self.assertEqual(config.language, "java")
            self.assertEqual(config.framework, "java")

    def test_init_workspace_supports_configuration_overrides(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text("<project></project>", encoding="utf-8")
            service = RuntimeService(workspace)
            service.path_setup.ensure_cli_on_user_path = lambda: {  # type: ignore[method-assign]
                "status": "unchanged",
                "path_added": False,
                "target": r"C:\demo\.venv\Scripts",
            }
            result = service.init_workspace(
                language="java",
                framework="spring-boot",
                template_root="custom-templates",
                build_command="mvn -q -DskipTests package",
                test_command="mvn -q test",
            )
            config = service.storage.load_workspace_config()
            self.assertEqual(config.language, "java")
            self.assertEqual(config.framework, "spring-boot")
            self.assertEqual(config.template_root, "custom-templates")
            self.assertEqual(config.script_commands["build"], "mvn -q -DskipTests package")
            self.assertEqual(config.validation_commands["test"], "mvn -q test")
            self.assertEqual(result["template_root"], str(workspace / "custom-templates"))
            self.assertTrue((workspace / "custom-templates").exists())
            self.assertEqual(
                service.storage.template_path("crud_generator"),
                workspace / "custom-templates" / "crud_generator.json",
            )

    def test_runtime_generates_feature_with_structured_spec(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text(
                """
                <project>
                  <modules>
                    <module>ruoyi-admin</module>
                    <module>ruoyi-em</module>
                  </modules>
                </project>
                """,
                encoding="utf-8",
            )
            sample = workspace / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "SampleController.java"
            sample.parent.mkdir(parents=True, exist_ok=True)
            sample.write_text("package com.ruoyi.em.controller;\npublic class SampleController {}\n", encoding="utf-8")
            service = RuntimeService(workspace)
            spec = {
                "name": "设备台账",
                "entity": "EmDeviceLedger",
                "comment": "设备台账",
                "table_name": "em_device_ledger",
                "route_path": "/em/deviceLedger",
                "permission_prefix": "em:deviceLedger",
                "response_wrapper": "ResultModel",
                "use_result_model": True,
                "fields": [
                    {"name": "id", "type": "Long", "column": "id", "comment": "主键ID", "query": "eq"},
                    {"name": "deviceName", "type": "String", "column": "device_name", "comment": "设备名称", "query": "like", "excel": True},
                    {"name": "useStatus", "type": "String", "column": "use_status", "comment": "使用状态", "query": "eq", "excel": True},
                ],
            }
            result = service.generate_feature("设备台账", entity_name="EmDeviceLedger", spec_data=spec)
            controller_path = Path(next(item["path"] for item in result["generated_files"] if item["kind"] == "controller"))
            bo_path = Path(next(item["path"] for item in result["generated_files"] if item["kind"] == "bo"))
            controller_text = controller_path.read_text(encoding="utf-8")
            bo_text = bo_path.read_text(encoding="utf-8")
            self.assertIn('@RequestMapping("/em/deviceLedger")', controller_text)
            self.assertIn("@PreAuthorize(\"@ss.hasPermi('em:deviceLedger:list')\")", controller_text)
            self.assertIn("ResultModel<TableDataInfo>", controller_text)
            self.assertIn("class EmDeviceLedgerBo", bo_text)
            mapper_xml_item = next((item for item in result["generated_files"] if item["kind"] == "mapper_xml"), None)
            if mapper_xml_item is not None:
                mapper_xml_text = Path(mapper_xml_item["path"]).read_text(encoding="utf-8")
                self.assertIn("from em_device_ledger", mapper_xml_text)
                self.assertIn("device_name", mapper_xml_text)

    def test_detects_fastapi_python(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "requirements.txt").write_text("fastapi\npytest\n", encoding="utf-8")
            analysis = ProjectDetector(workspace).detect()
            self.assertEqual(analysis.language, "python")
            self.assertEqual(analysis.framework, "fastapi")
            self.assertEqual(analysis.test_framework, "pytest")

    def test_detects_nextjs(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "package.json").write_text(
                '{"dependencies":{"next":"14.0.0","typescript":"5.0.0"}}',
                encoding="utf-8",
            )
            analysis = ProjectDetector(workspace).detect()
            self.assertEqual(analysis.language, "typescript")
            self.assertEqual(analysis.framework, "nextjs")


if __name__ == "__main__":
    unittest.main()
