from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from aicodegen.configurator import WorkspaceConfigurator
from aicodegen.detector import ProjectDetector
from aicodegen.generator import CrudGenerator, FeaturePlanner, SqlSpecParser
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
            config = WorkspaceConfigurator().build(analysis)
            self.assertEqual(config.tools["crud_generator"].config["module_name"], "")
            self.assertEqual(config.tools["crud_generator"].config["domain_package"], "com.example.domain")

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

    def test_detects_nested_backend_and_frontend_workspace(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            nested_backend = workspace / "e-hospital-server" / "ehospital"
            nested_backend.mkdir(parents=True, exist_ok=True)
            (nested_backend / "pom.xml").write_text(
                """
                <project>
                  <parent>
                    <groupId>org.springframework.boot</groupId>
                    <artifactId>spring-boot-starter-parent</artifactId>
                    <version>3.2.5</version>
                  </parent>
                  <modules>
                    <module>ehospital-core</module>
                    <module>ehospital-miniprogram</module>
                  </modules>
                  <dependencies>
                    <dependency>
                      <groupId>org.springframework.boot</groupId>
                      <artifactId>spring-boot-starter-test</artifactId>
                    </dependency>
                  </dependencies>
                </project>
                """,
                encoding="utf-8",
            )
            java_file = nested_backend / "ehospital-miniprogram" / "src" / "main" / "java" / "com" / "xjzy" / "mc" / "ehospital" / "miniprogram" / "controller" / "DemoController.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.xjzy.mc.ehospital.miniprogram.controller;\npublic class DemoController {}\n",
                encoding="utf-8",
            )
            web = workspace / "e-hospital-web"
            web.mkdir(parents=True, exist_ok=True)
            (web / "package.json").write_text(
                """
                {
                  "dependencies": {
                    "vue": "^3.0.0"
                  },
                  "devDependencies": {
                    "vite": "^5.0.0"
                  }
                }
                """,
                encoding="utf-8",
            )
            analysis = ProjectDetector(workspace).detect()
            self.assertEqual(analysis.language, "java")
            self.assertEqual(analysis.build_tool, "maven")
            self.assertEqual(analysis.framework, "spring-boot")
            self.assertEqual(analysis.architecture, "multi-module")
            self.assertEqual(analysis.hints["project_root"], "e-hospital-server/ehospital")
            self.assertEqual(analysis.hints["workspace_layout"], "mixed-workspace")
            self.assertIn("e-hospital-web", analysis.hints["frontend_projects"])
            config = WorkspaceConfigurator().build(analysis)
            self.assertEqual(config.project_profile["project_root"], "e-hospital-server/ehospital")

    def test_generates_ruoyi_crud_files_in_nested_backend_workspace(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            backend = workspace / "backend"
            backend.mkdir(parents=True, exist_ok=True)
            (backend / "pom.xml").write_text(
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
            java_file = backend / "ruoyi-em" / "src" / "main" / "java" / "com" / "ruoyi" / "em" / "controller" / "DemoController.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.ruoyi.em.controller;\npublic class DemoController {}\n",
                encoding="utf-8",
            )
            mapper_xml = backend / "ruoyi-em" / "src" / "main" / "resources" / "mapper" / "em" / "DemoMapper.xml"
            mapper_xml.parent.mkdir(parents=True, exist_ok=True)
            mapper_xml.write_text("<mapper></mapper>", encoding="utf-8")
            frontend = workspace / "web"
            frontend.mkdir(parents=True, exist_ok=True)
            (frontend / "package.json").write_text('{"dependencies":{"vue":"^3.0.0"}}', encoding="utf-8")

            analysis = ProjectDetector(workspace).detect()
            self.assertEqual(analysis.hints["project_root"], "backend")
            tools_config = WorkspaceConfigurator().build(analysis)
            generated = CrudGenerator(workspace, tools_config).generate("LampPlan", comment="灯具方案")
            generated_paths = {item.kind: item.path for item in generated}
            self.assertTrue(generated_paths["domain"].exists())
            self.assertIn(str(backend / "ruoyi-em"), str(generated_paths["domain"]))

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
            for kind in ("domain", "bo", "vo", "mapper", "service", "service_impl", "controller"):
                self.assertIn("Generated by aicodegen.", generated_paths[kind].read_text(encoding="utf-8"))
            self.assertIn("package com.ruoyi.em.controller;", controller_content)
            self.assertIn("@RequestMapping(\"/lamp-plan\")", controller_content)
            mapper_xml_content = generated_paths["mapper_xml"].read_text(encoding="utf-8")
            self.assertIn("namespace=\"com.ruoyi.em.mapper.LampPlanMapper\"", mapper_xml_content)
            service_impl_content = generated_paths["service_impl"].read_text(encoding="utf-8")
            self.assertIn("public int deleteLampPlanByIds(Long[] ids)", service_impl_content)
            self.assertIn("public int deleteLampPlanById(Long id)", service_impl_content)
            self.assertIn("lampPlanService.deleteLampPlanByIds(ids)", controller_content)

    def test_generates_standard_spring_controller_without_ruoyi_dependencies(self) -> None:
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
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "src" / "main" / "java" / "com" / "demo" / "mini" / "DemoApplication.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text("package com.demo.mini;\npublic class DemoApplication {}\n", encoding="utf-8")

            analysis = ProjectDetector(workspace).detect()
            tools_config = WorkspaceConfigurator().build(analysis)
            generated = CrudGenerator(workspace, tools_config).generate("DeviceLedger", comment="设备台账")
            generated_paths = {item.kind: item.path for item in generated}
            controller_content = generated_paths["controller"].read_text(encoding="utf-8")
            self.assertIn("import org.springframework.http.ResponseEntity;", controller_content)
            self.assertIn("public ResponseEntity<List<DeviceLedgerVo>> list", controller_content)
            self.assertIn("return ResponseEntity.ok(deviceLedgerService.selectDeviceLedgerList(query));", controller_content)
            self.assertNotIn("AjaxResult", controller_content)
            self.assertNotIn("com.ruoyi", controller_content)
            self.assertNotIn("Slf4j", controller_content)

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
            self.assertEqual(result["lifecycle_state"], "verified")
            self.assertEqual(result["template"]["strategy"], "learned-from-project")
            self.assertEqual(result["template"]["template_version"], 1)
            self.assertIn("learned_at", result["template"])
            self.assertIn("verified_at", result["template"])
            self.assertIn("SampleController.java", result["template"]["examples"]["controller"])
            status = service.status()
            self.assertEqual(status["tools"]["crud_generator"]["status"], "verified")
            self.assertEqual(status["tools"]["crud_generator"]["metadata"]["template_version"], 1)

    def test_ensure_template_marks_invalid_config_failed(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            service = RuntimeService(workspace)
            service.storage.ensure()
            analysis = ProjectDetector(workspace).detect()
            tools_config = WorkspaceConfigurator().build(analysis)
            tools_config.tools["crud_generator"].config = {"template_profile": "ruoyi-mybatis"}

            result = service.template_manager.ensure_template("crud_generator", analysis, tools_config)
            self.assertEqual(result["lifecycle_state"], "failed")
            self.assertTrue(result["is_error"])
            self.assertIn("domain_package", tools_config.tools["crud_generator"].last_error)

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

    def test_generates_entity_for_single_module_spring_workspace(self) -> None:
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
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "src" / "main" / "java" / "com" / "demo" / "mini" / "DemoApplication.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.demo.mini;\npublic class DemoApplication {}\n",
                encoding="utf-8",
            )
            service = RuntimeService(workspace)
            service.init_workspace()
            generated = CrudGenerator(workspace, service.prepare_tools_config_for_generation()).generate_entity("DeviceLedger", comment="设备台账")
            self.assertTrue(generated.path.exists())
            self.assertEqual(generated.path, workspace / "src" / "main" / "java" / "com" / "demo" / "mini" / "domain" / "DeviceLedger.java")

    def test_runtime_prepare_tools_config_recovers_single_module_java_workspace(self) -> None:
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
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "src" / "main" / "java" / "com" / "demo" / "mini" / "DemoApplication.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.demo.mini;\npublic class DemoApplication {}\n",
                encoding="utf-8",
            )
            service = RuntimeService(workspace)
            service.storage.ensure()
            service.storage.tools_path.write_text(
                '{"enabled_tools":[],"suggested_tools":["crud_generator"],"project_profile":{"language":"java","framework":"spring-boot","build_tool":"maven","orm":"unknown","base_package":"com.demo.mini","architecture":"standard","modules":[],"project_root":"","frontend_projects":[],"backend_projects":[]},"tools":{"crud_generator":{"status":"learned","config":{"template_profile":"spring-generic","project_root":"","base_package":"com.demo.mini","orm":"unknown"},"metadata":{},"last_error":""}}}',
                encoding="utf-8",
            )
            tools_config = service.prepare_tools_config_for_generation()
            crud_config = tools_config.tools["crud_generator"].config
            self.assertEqual(crud_config["module_name"], "")
            self.assertEqual(crud_config["controller_package"], "com.demo.mini.controller")

    def test_feature_planner_infers_entity_name(self) -> None:
        planner = FeaturePlanner()
        self.assertEqual(planner.infer_entity_name("设备台账"), "DeviceLedger")
        self.assertEqual(planner.infer_entity_name("lamp plan"), "LampPlan")
        self.assertEqual(planner.infer_entity_name("用户管理", explicit_entity="UserAccount"), "UserAccount")

    def test_sql_spec_parser_uses_create_table_as_source_of_truth(self) -> None:
        ddl = """
        CREATE TABLE `em_device_ledger` (
          `id` bigint NOT NULL COMMENT '主键ID',
          `device_name` varchar(64) NOT NULL COMMENT '设备名称',
          `purchase_amount` decimal(12,2) DEFAULT NULL COMMENT '采购金额',
          `use_status` char(1) DEFAULT NULL COMMENT '使用状态',
          `create_time` datetime DEFAULT NULL COMMENT '创建时间',
          PRIMARY KEY (`id`)
        ) COMMENT='设备台账';
        """
        spec = SqlSpecParser().parse(ddl, fallback_name="设备台账")
        self.assertEqual(spec.entity, "EmDeviceLedger")
        self.assertEqual(spec.table_name, "em_device_ledger")
        self.assertEqual(spec.comment, "设备台账")
        self.assertEqual(spec.route_path, "/em-device-ledger")
        self.assertEqual(spec.permission_prefix, "em:deviceLedger")
        fields = {field.name: field for field in spec.fields}
        self.assertEqual(fields["deviceName"].type, "String")
        self.assertEqual(fields["purchaseAmount"].type, "BigDecimal")
        self.assertEqual(fields["createTime"].type, "LocalDateTime")
        self.assertEqual(fields["deviceName"].comment, "设备名称")

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
            self.assertIn("doctor", names)
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

    def test_runtime_refuses_failed_template_generation(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text("<project></project>", encoding="utf-8")
            service = RuntimeService(workspace)
            service.storage.ensure()
            template_path = service.storage.template_path("crud_generator")
            template_path.write_text(
                '{"tool_name":"crud_generator","lifecycle_state":"failed","last_error":"broken template"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "broken template"):
                service.generate_feature("设备台账")

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

    def test_ensure_template_runs_configured_validation_commands(self) -> None:
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
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "src" / "main" / "java" / "com" / "demo" / "mini" / "DemoApplication.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text("package com.demo.mini;\npublic class DemoApplication {}\n", encoding="utf-8")
            service = RuntimeService(workspace)
            service.path_setup.ensure_cli_on_user_path = lambda: {"status": "unchanged", "path_added": False, "target": ""}
            service.init_workspace(
                build_command='python -c "print(\'build-ok\')"',
                test_command='python -c "print(\'test-ok\')"',
            )

            result = service.ensure_template("crud_generator")
            self.assertEqual(result["lifecycle_state"], "verified")
            self.assertTrue(result["validation"]["ok"])
            outputs = "\n".join(str(item["stdout"]) for item in result["validation"]["commands"])
            self.assertIn("build-ok", outputs)
            self.assertIn("test-ok", outputs)

    def test_generation_fails_when_configured_validation_command_fails(self) -> None:
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
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "src" / "main" / "java" / "com" / "demo" / "mini" / "DemoApplication.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text("package com.demo.mini;\npublic class DemoApplication {}\n", encoding="utf-8")
            service = RuntimeService(workspace)
            service.path_setup.ensure_cli_on_user_path = lambda: {"status": "unchanged", "path_added": False, "target": ""}
            service.init_workspace(test_command='python -c "import sys; sys.exit(7)"')

            with self.assertRaisesRegex(RuntimeError, "test command failed"):
                service.generate_feature("设备台账")
            status = service.status()
            self.assertEqual(status["tools"]["crud_generator"]["status"], "failed")
            self.assertIn("exit code 7", status["tools"]["crud_generator"]["last_error"])

    def test_doctor_reports_workspace_readiness(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pom.xml").write_text("<project></project>", encoding="utf-8")
            service = RuntimeService(workspace)
            not_ready = service.doctor()
            self.assertFalse(not_ready["ready"])
            self.assertIn("workspace_not_initialized", {item["code"] for item in not_ready["checks"]})

            service.init_workspace()
            ready = service.doctor()
            self.assertTrue(ready["ready"])
            self.assertEqual(ready["workspace"], str(workspace))

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

    def test_runtime_generates_feature_from_sql_ddl(self) -> None:
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
            mapper_xml = workspace / "ruoyi-em" / "src" / "main" / "resources" / "mapper" / "em" / "SampleMapper.xml"
            mapper_xml.parent.mkdir(parents=True, exist_ok=True)
            mapper_xml.write_text("<mapper></mapper>", encoding="utf-8")
            ddl = """
            CREATE TABLE `em_device_ledger` (
              `id` bigint NOT NULL COMMENT '主键ID',
              `device_name` varchar(64) NOT NULL COMMENT '设备名称',
              `purchase_amount` decimal(12,2) DEFAULT NULL COMMENT '采购金额',
              `use_status` char(1) DEFAULT NULL COMMENT '使用状态',
              PRIMARY KEY (`id`)
            ) COMMENT='设备台账';
            """
            result = RuntimeService(workspace).generate_feature("设备台账", sql=ddl)
            self.assertEqual(result["source"], "sql")
            self.assertEqual(result["entity_name"], "EmDeviceLedger")
            self.assertEqual(result["feature_spec"]["table_name"], "em_device_ledger")
            domain_path = Path(next(item["path"] for item in result["generated_files"] if item["kind"] == "domain"))
            mapper_xml_path = Path(next(item["path"] for item in result["generated_files"] if item["kind"] == "mapper_xml"))
            domain_text = domain_path.read_text(encoding="utf-8")
            mapper_xml_text = mapper_xml_path.read_text(encoding="utf-8")
            self.assertIn("private String deviceName;", domain_text)
            self.assertIn("private BigDecimal purchaseAmount;", domain_text)
            self.assertIn("from em_device_ledger", mapper_xml_text)
            self.assertIn("purchase_amount", mapper_xml_text)

    def test_runtime_generates_standard_spring_feature_from_sql_without_ruoyi_dependencies(self) -> None:
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
                </project>
                """,
                encoding="utf-8",
            )
            java_file = workspace / "src" / "main" / "java" / "com" / "demo" / "mini" / "DemoApplication.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text("package com.demo.mini;\npublic class DemoApplication {}\n", encoding="utf-8")
            ddl = """
            CREATE TABLE `sql_notice_record` (
              `id` bigint NOT NULL COMMENT '主键ID',
              `notice_title` varchar(128) NOT NULL COMMENT '通知标题',
              `notice_amount` decimal(12,2) DEFAULT NULL COMMENT '通知金额',
              `create_time` datetime DEFAULT NULL COMMENT '创建时间',
              PRIMARY KEY (`id`)
            ) COMMENT='SQL通知记录';
            """
            result = RuntimeService(workspace).generate_feature("SQL通知记录", sql=ddl)
            self.assertEqual(result["entity_name"], "SqlNoticeRecord")
            controller_path = Path(next(item["path"] for item in result["generated_files"] if item["kind"] == "controller"))
            domain_path = Path(next(item["path"] for item in result["generated_files"] if item["kind"] == "domain"))
            controller_text = controller_path.read_text(encoding="utf-8")
            domain_text = domain_path.read_text(encoding="utf-8")
            self.assertIn("ResponseEntity<List<SqlNoticeRecordVo>>", controller_text)
            self.assertIn("private BigDecimal noticeAmount;", domain_text)
            self.assertIn("private LocalDateTime createTime;", domain_text)
            self.assertNotIn("com.ruoyi", controller_text)
            self.assertNotIn("AjaxResult", controller_text)
            self.assertNotIn("@Excel", domain_text)

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
