from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .models import FeatureSpec, FieldSpec, ToolsConfig


@dataclass
class GeneratedFile:
    path: Path
    kind: str


class CrudGenerator:
    def __init__(self, workspace: Path, tools_config: ToolsConfig) -> None:
        self.workspace = workspace
        self.tools_config = tools_config

    def generate(
        self,
        entity_name: str,
        *,
        comment: str | None = None,
        spec: FeatureSpec | None = None,
    ) -> list[GeneratedFile]:
        tool = self.tools_config.tools.get("crud_generator")
        if tool is None:
            raise ValueError("crud_generator is not configured for this workspace.")

        config = tool.config
        module_name = config.get("module_name") or self.tools_config.project_profile.get("business_module") or ""
        if not module_name or module_name == "unknown":
            raise ValueError("Workspace is missing a target module for crud generation.")

        entity_name = self._normalize_entity_name(entity_name)
        feature_spec = self._prepare_spec(entity_name, comment=comment, spec=spec)
        module_dir = self.workspace / module_name

        domain_package = config["domain_package"]
        mapper_package = config["mapper_package"]
        service_package = config["service_package"]
        controller_package = config["controller_package"]
        bo_package = feature_spec.bo_package or self._derive_bo_package(controller_package)
        vo_package = feature_spec.vo_package or self._derive_vo_package(controller_package)
        mapper_xml = bool(config.get("mapper_xml", True))

        generated: list[GeneratedFile] = []

        domain_path = self._java_path(module_dir, domain_package, f"{entity_name}.java")
        bo_path = self._java_path(module_dir, bo_package, f"{feature_spec.bo_name}.java")
        vo_path = self._java_path(module_dir, vo_package, f"{feature_spec.vo_name}.java")
        mapper_path = self._java_path(module_dir, mapper_package, f"{entity_name}Mapper.java")
        service_path = self._java_path(module_dir, service_package, f"I{entity_name}Service.java")
        service_impl_path = self._java_path(module_dir, f"{service_package}.impl", f"{entity_name}ServiceImpl.java")
        controller_path = self._java_path(module_dir, controller_package, f"{entity_name}Controller.java")

        self._write_file(
            domain_path,
            self._domain_template(domain_package, entity_name, feature_spec.comment, feature_spec.fields, config.get("entity_base_class", "BaseEntity")),
        )
        generated.append(GeneratedFile(domain_path, "domain"))

        self._write_file(
            bo_path,
            self._dto_template(bo_package, feature_spec.bo_name, feature_spec.comment, feature_spec.fields, "业务对象"),
        )
        generated.append(GeneratedFile(bo_path, "bo"))

        self._write_file(
            vo_path,
            self._dto_template(vo_package, feature_spec.vo_name, feature_spec.comment, feature_spec.fields, "视图对象"),
        )
        generated.append(GeneratedFile(vo_path, "vo"))

        self._write_file(
            mapper_path,
            self._mapper_template(mapper_package, domain_package, bo_package, vo_package, entity_name, feature_spec.bo_name, feature_spec.vo_name),
        )
        generated.append(GeneratedFile(mapper_path, "mapper"))

        self._write_file(
            service_path,
            self._service_template(service_package, domain_package, bo_package, vo_package, entity_name, feature_spec.bo_name, feature_spec.vo_name),
        )
        generated.append(GeneratedFile(service_path, "service"))

        self._write_file(
            service_impl_path,
            self._service_impl_template(
                service_package,
                mapper_package,
                domain_package,
                bo_package,
                vo_package,
                entity_name,
                feature_spec.bo_name,
                feature_spec.vo_name,
            ),
        )
        generated.append(GeneratedFile(service_impl_path, "service_impl"))

        self._write_file(
            controller_path,
            self._controller_template(
                controller_package,
                service_package,
                domain_package,
                bo_package,
                vo_package,
                entity_name,
                feature_spec,
                config.get("controller_base_class", "BaseController"),
            ),
        )
        generated.append(GeneratedFile(controller_path, "controller"))

        if mapper_xml:
            mapper_xml_path = self._mapper_xml_path(module_dir, entity_name)
            self._write_file(
                mapper_xml_path,
                self._mapper_xml_template(mapper_package, domain_package, bo_package, vo_package, entity_name, feature_spec),
            )
            generated.append(GeneratedFile(mapper_xml_path, "mapper_xml"))

        return generated

    def generate_entity(
        self,
        entity_name: str,
        *,
        comment: str | None = None,
        spec: FeatureSpec | None = None,
    ) -> GeneratedFile:
        tool = self.tools_config.tools.get("crud_generator")
        if tool is None:
            raise ValueError("crud_generator is not configured for this workspace.")
        config = tool.config
        module_name = config.get("module_name") or self.tools_config.project_profile.get("business_module") or ""
        if not module_name or module_name == "unknown":
            raise ValueError("Workspace is missing a target module for entity generation.")
        entity_name = self._normalize_entity_name(entity_name)
        feature_spec = self._prepare_spec(entity_name, comment=comment, spec=spec)
        module_dir = self.workspace / module_name
        domain_package = config["domain_package"]
        domain_path = self._java_path(module_dir, domain_package, f"{entity_name}.java")
        self._write_file(
            domain_path,
            self._domain_template(domain_package, entity_name, feature_spec.comment, feature_spec.fields, config.get("entity_base_class", "BaseEntity")),
        )
        return GeneratedFile(domain_path, "domain")

    def _prepare_spec(self, entity_name: str, *, comment: str | None, spec: FeatureSpec | None) -> FeatureSpec:
        if spec is not None:
            normalized = FeatureSpec.from_dict(spec.to_dict())
            normalized.entity = entity_name
            normalized.comment = normalized.comment or comment or normalized.name or entity_name
            normalized.bo_name = normalized.bo_name or f"{entity_name}Bo"
            normalized.vo_name = normalized.vo_name or f"{entity_name}Vo"
            normalized.table_name = normalized.table_name or self._snake_name(entity_name)
            normalized.route_path = normalized.route_path or self._default_route(entity_name)
            normalized.permission_prefix = normalized.permission_prefix or self._default_permission(entity_name)
            return normalized
        return FeatureSpec(
            name=comment or entity_name,
            entity=entity_name,
            comment=comment or entity_name,
            table_name=self._snake_name(entity_name),
            route_path=self._default_kebab_route(entity_name),
            permission_prefix=self._default_permission(entity_name),
            bo_name=f"{entity_name}Bo",
            vo_name=f"{entity_name}Vo",
            fields=[],
        )

    def _java_path(self, module_dir: Path, package_name: str, filename: str) -> Path:
        package_dir = Path(*package_name.split("."))
        return module_dir / "src" / "main" / "java" / package_dir / filename

    def _mapper_xml_path(self, module_dir: Path, entity_name: str) -> Path:
        module_hint = self.tools_config.project_profile.get("business_module", "")
        suffix = module_hint.removeprefix("ruoyi-") if isinstance(module_hint, str) else ""
        parts = ["mapper"]
        if suffix:
            parts.append(suffix)
        return module_dir / "src" / "main" / "resources" / Path(*parts) / f"{entity_name}Mapper.xml"

    def _write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _normalize_entity_name(self, entity_name: str) -> str:
        pieces = re.split(r"[^A-Za-z0-9]+", entity_name)
        merged = "".join(piece[:1].upper() + piece[1:] for piece in pieces if piece)
        if not merged:
            raise ValueError("Entity name must contain letters or numbers.")
        return merged

    def _camel_name(self, entity_name: str) -> str:
        return entity_name[:1].lower() + entity_name[1:]

    def _snake_name(self, entity_name: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", entity_name).lower()

    def _default_route(self, entity_name: str) -> str:
        module_hint = str(self.tools_config.project_profile.get("business_module", "") or "")
        module_segment = module_hint.removeprefix("ruoyi-") if module_hint else ""
        camel = self._camel_name(entity_name)
        if module_segment:
            return f"/{module_segment}/{camel}"
        return f"/{camel}"

    def _default_kebab_route(self, entity_name: str) -> str:
        kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", entity_name).lower()
        return f"/{kebab}"

    def _default_permission(self, entity_name: str) -> str:
        module_hint = str(self.tools_config.project_profile.get("business_module", "") or "")
        module_segment = module_hint.removeprefix("ruoyi-") if module_hint else "system"
        return f"{module_segment}:{self._camel_name(entity_name)}"

    def _derive_bo_package(self, controller_package: str) -> str:
        return controller_package.rsplit(".", 1)[0] + ".pojo.bo"

    def _derive_vo_package(self, controller_package: str) -> str:
        return controller_package.rsplit(".", 1)[0] + ".pojo.vo"

    def _java_imports_for_fields(self, fields: list[FieldSpec]) -> list[str]:
        imports: set[str] = set()
        known = {
            "BigDecimal": "java.math.BigDecimal",
            "Date": "java.util.Date",
            "LocalDate": "java.time.LocalDate",
            "LocalDateTime": "java.time.LocalDateTime",
            "LocalTime": "java.time.LocalTime",
        }
        for field in fields:
            java_type = field.type.strip()
            if java_type in known:
                imports.add(known[java_type])
            elif "." in java_type and not java_type.startswith("java.lang."):
                imports.add(java_type)
        return sorted(imports)

    def _simple_type(self, type_name: str) -> str:
        return type_name.split(".")[-1]

    def _domain_template(
        self,
        package_name: str,
        entity_name: str,
        comment: str,
        fields: list[FieldSpec],
        entity_base_class: str,
    ) -> str:
        imports = self._java_imports_for_fields(fields)
        has_excel = any(field.excel for field in fields)
        base_import = "com.ruoyi.common.core.domain.BaseEntity" if entity_base_class == "BaseEntity" else ""
        import_lines = []
        if base_import:
            import_lines.append(f"import {base_import};")
        if has_excel:
            import_lines.append("import com.ruoyi.common.annotation.Excel;")
        import_lines.append("import lombok.Data;")
        import_lines.extend(f"import {item};" for item in imports)
        import_block = "\n".join(import_lines)
        field_block = self._field_block(fields, with_excel=True)
        base_extends = f" extends {entity_base_class}" if entity_base_class != "unknown" else ""
        return (
            f"package {package_name};\n\n"
            f"{import_block}\n\n"
            "/**\n"
            f" * {comment}对象 {entity_name}\n"
            " */\n"
            "@Data\n"
            f"public class {entity_name}{base_extends} {{\n"
            "    private static final long serialVersionUID = 1L;\n\n"
            f"{field_block}"
            "}\n"
        )

    def _dto_template(
        self,
        package_name: str,
        class_name: str,
        comment: str,
        fields: list[FieldSpec],
        kind: str,
    ) -> str:
        imports = self._java_imports_for_fields(fields)
        import_lines = ["import java.io.Serializable;", "import lombok.Data;"]
        import_lines.extend(f"import {item};" for item in imports)
        import_block = "\n".join(import_lines)
        field_block = self._field_block(fields, with_excel=False)
        return (
            f"package {package_name};\n\n"
            f"{import_block}\n\n"
            "/**\n"
            f" * {comment}{kind} {class_name}\n"
            " */\n"
            "@Data\n"
            f"public class {class_name} implements Serializable {{\n"
            "    private static final long serialVersionUID = 1L;\n\n"
            f"{field_block}"
            "}\n"
        )

    def _field_block(self, fields: list[FieldSpec], *, with_excel: bool) -> str:
        if not fields:
            return "    /**\n     * TODO: add fields\n     */\n"
        chunks: list[str] = []
        for field in fields:
            chunks.append("    /**")
            chunks.append(f"     * {field.comment or field.name}")
            chunks.append("     */")
            if with_excel and field.excel:
                chunks.append(f"    @Excel(name = \"{field.comment or field.name}\")")
            chunks.append(f"    private {self._simple_type(field.type)} {field.name};")
            chunks.append("")
        return "\n".join(chunks[:-1]) + "\n"

    def _mapper_template(
        self,
        mapper_package: str,
        domain_package: str,
        bo_package: str,
        vo_package: str,
        entity_name: str,
        bo_name: str,
        vo_name: str,
    ) -> str:
        return (
            f"package {mapper_package};\n\n"
            "import java.util.List;\n"
            f"import {domain_package}.{entity_name};\n"
            f"import {bo_package}.{bo_name};\n"
            f"import {vo_package}.{vo_name};\n\n"
            f"public interface {entity_name}Mapper {{\n"
            f"    {entity_name} select{entity_name}ById(Long id);\n\n"
            f"    List<{vo_name}> select{entity_name}List({bo_name} query);\n\n"
            f"    int insert{entity_name}({bo_name} command);\n\n"
            f"    int update{entity_name}({bo_name} command);\n\n"
            f"    int delete{entity_name}ById(Long id);\n\n"
            f"    int delete{entity_name}ByIds(Long[] ids);\n"
            "}\n"
        )

    def _service_template(
        self,
        service_package: str,
        domain_package: str,
        bo_package: str,
        vo_package: str,
        entity_name: str,
        bo_name: str,
        vo_name: str,
    ) -> str:
        return (
            f"package {service_package};\n\n"
            "import java.util.List;\n"
            f"import {domain_package}.{entity_name};\n"
            f"import {bo_package}.{bo_name};\n"
            f"import {vo_package}.{vo_name};\n\n"
            f"public interface I{entity_name}Service {{\n"
            f"    {entity_name} select{entity_name}ById(Long id);\n\n"
            f"    List<{vo_name}> select{entity_name}List({bo_name} query);\n\n"
            f"    int insert{entity_name}({bo_name} command);\n\n"
            f"    int update{entity_name}({bo_name} command);\n\n"
            f"    int delete{entity_name}ByIds(Long[] ids);\n\n"
            f"    int delete{entity_name}ById(Long id);\n"
            "}\n"
        )

    def _service_impl_template(
        self,
        service_package: str,
        mapper_package: str,
        domain_package: str,
        bo_package: str,
        vo_package: str,
        entity_name: str,
        bo_name: str,
        vo_name: str,
    ) -> str:
        impl_package = f"{service_package}.impl"
        mapper_var = self._camel_name(f"{entity_name}Mapper")
        return (
            f"package {impl_package};\n\n"
            "import java.util.List;\n"
            f"import {mapper_package}.{entity_name}Mapper;\n"
            f"import {domain_package}.{entity_name};\n"
            f"import {bo_package}.{bo_name};\n"
            f"import {vo_package}.{vo_name};\n"
            f"import {service_package}.I{entity_name}Service;\n"
            "import org.springframework.beans.factory.annotation.Autowired;\n"
            "import org.springframework.stereotype.Service;\n\n"
            "@Service\n"
            f"public class {entity_name}ServiceImpl implements I{entity_name}Service {{\n"
            "    @Autowired\n"
            f"    private {entity_name}Mapper {mapper_var};\n\n"
            "    @Override\n"
            f"    public {entity_name} select{entity_name}ById(Long id) {{\n"
            f"        return {mapper_var}.select{entity_name}ById(id);\n"
            "    }\n\n"
            "    @Override\n"
            f"    public List<{vo_name}> select{entity_name}List({bo_name} query) {{\n"
            f"        return {mapper_var}.select{entity_name}List(query);\n"
            "    }\n\n"
            "    @Override\n"
            f"    public int insert{entity_name}({bo_name} command) {{\n"
            f"        return {mapper_var}.insert{entity_name}(command);\n"
            "    }\n\n"
            "    @Override\n"
            f"    public int update{entity_name}({bo_name} command) {{\n"
            f"        return {mapper_var}.update{entity_name}(command);\n"
            "    }\n\n"
            "    @Override\n"
            "    public int deleteByIds(Long[] ids) {\n"
            f"        return {mapper_var}.delete{entity_name}ByIds(ids);\n"
            "    }\n\n"
            "    @Override\n"
            "    public int deleteById(Long id) {\n"
            f"        return {mapper_var}.delete{entity_name}ById(id);\n"
            "    }\n"
            "}\n"
        )

    def _controller_template(
        self,
        controller_package: str,
        service_package: str,
        domain_package: str,
        bo_package: str,
        vo_package: str,
        entity_name: str,
        spec: FeatureSpec,
        controller_base_class: str,
    ) -> str:
        camel = self._camel_name(entity_name)
        service_field_type = f"I{entity_name}Service"
        imports = [
            "import java.util.List;",
            f"import {domain_package}.{entity_name};",
            f"import {bo_package}.{spec.bo_name};",
            f"import {vo_package}.{spec.vo_name};",
            f"import {service_package}.{service_field_type};",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "import org.springframework.web.bind.annotation.DeleteMapping;",
            "import org.springframework.web.bind.annotation.GetMapping;",
            "import org.springframework.web.bind.annotation.PathVariable;",
            "import org.springframework.web.bind.annotation.PostMapping;",
            "import org.springframework.web.bind.annotation.PutMapping;",
            "import org.springframework.web.bind.annotation.RequestBody;",
            "import org.springframework.web.bind.annotation.RequestMapping;",
            "import org.springframework.web.bind.annotation.RestController;",
        ]
        if spec.use_pre_authorize:
            imports.append("import org.springframework.security.access.prepost.PreAuthorize;")
        if spec.use_log:
            imports.extend(
                [
                    "import com.ruoyi.common.annotation.Log;",
                    "import com.ruoyi.common.enums.BusinessType;",
                ]
            )
        if spec.use_result_model:
            imports.extend(
                [
                    "import com.ruoyi.common.base.ResultModel;",
                    "import com.ruoyi.common.core.page.TableDataInfo;",
                ]
            )
        elif spec.response_wrapper == "AjaxResult":
            imports.append("import com.ruoyi.common.core.domain.AjaxResult;")
        if controller_base_class == "BaseController":
            imports.append("import com.ruoyi.common.core.controller.BaseController;")
        if spec.use_slf4j:
            imports.append("import lombok.extern.slf4j.Slf4j;")
        imports_block = "\n".join(imports)
        extends_clause = f" extends {controller_base_class}" if controller_base_class != "unknown" else ""
        list_return = "ResultModel<TableDataInfo>" if spec.use_result_model else "AjaxResult"
        item_return = f"ResultModel<{entity_name}>" if spec.use_result_model else "AjaxResult"
        write_return = "ResultModel<Integer>" if spec.use_result_model else "AjaxResult"
        list_body = (
            "        startPage();\n"
            f"        List<{spec.vo_name}> list = {camel}Service.select{entity_name}List(query);\n"
            "        TableDataInfo dataInfo = getDataTable(list);\n"
            "        return ResultModel.success(dataInfo);\n"
            if spec.use_result_model
            else f"        return AjaxResult.success({camel}Service.select{entity_name}List(query));\n"
        )
        wrap_success = "ResultModel.success" if spec.use_result_model else "AjaxResult.success"
        pre = self._preauthorize
        log = self._log_annotation
        slf4j = "@Slf4j\n" if spec.use_slf4j else ""
        return (
            f"package {controller_package};\n\n"
            f"{imports_block}\n\n"
            "/**\n"
            f" * {spec.comment}Controller\n"
            " */\n"
            f"{slf4j}"
            "@RestController\n"
            f"@RequestMapping(\"{spec.route_path}\")\n"
            f"public class {entity_name}Controller{extends_clause} {{\n"
            "    @Autowired\n"
            f"    private {service_field_type} {camel}Service;\n\n"
            f"{pre(spec, 'list')}"
            "    @GetMapping(\"/list\")\n"
            f"    public {list_return} list({spec.bo_name} query) {{\n"
            f"{list_body}"
            "    }\n\n"
            f"{pre(spec, 'list')}"
            "    @GetMapping(value = \"/{id}\")\n"
            f"    public {item_return} getInfo(@PathVariable(\"id\") Long id) {{\n"
            f"        return {wrap_success}({camel}Service.select{entity_name}ById(id));\n"
            "    }\n\n"
            f"{pre(spec, 'add')}"
            f"{log(spec, 'INSERT')}"
            "    @PostMapping\n"
            f"    public {write_return} add(@RequestBody {spec.bo_name} command) {{\n"
            f"        return {wrap_success}({camel}Service.insert{entity_name}(command));\n"
            "    }\n\n"
            f"{pre(spec, 'edit')}"
            f"{log(spec, 'UPDATE')}"
            "    @PutMapping\n"
            f"    public {write_return} edit(@RequestBody {spec.bo_name} command) {{\n"
            f"        return {wrap_success}({camel}Service.update{entity_name}(command));\n"
            "    }\n\n"
            f"{pre(spec, 'remove')}"
            f"{log(spec, 'DELETE')}"
            "    @DeleteMapping(\"/{ids}\")\n"
            f"    public {write_return} remove(@PathVariable Long[] ids) {{\n"
            f"        return {wrap_success}({camel}Service.deleteByIds(ids));\n"
            "    }\n"
            "}\n"
        )

    def _preauthorize(self, spec: FeatureSpec, action: str) -> str:
        if not spec.use_pre_authorize:
            return ""
        return f"    @PreAuthorize(\"@ss.hasPermi('{spec.permission_prefix}:{action}')\")\n"

    def _log_annotation(self, spec: FeatureSpec, business_type: str) -> str:
        if not spec.use_log:
            return ""
        return f"    @Log(title = \"{spec.comment}\", businessType = BusinessType.{business_type})\n"

    def _mapper_xml_template(
        self,
        mapper_package: str,
        domain_package: str,
        bo_package: str,
        vo_package: str,
        entity_name: str,
        spec: FeatureSpec,
    ) -> str:
        columns = ", ".join(field.column for field in spec.fields) if spec.fields else "*"
        result_map = "\n".join(
            f"        <result property=\"{field.name}\" column=\"{field.column}\" />"
            for field in spec.fields
        ) or "        <!-- TODO: define column mappings -->"
        where_lines = []
        for field in spec.fields:
            if field.query == "like":
                where_lines.append(
                    f"            <if test=\"{field.name} != null and {field.name} != ''\"> and {field.column} like concat('%', #{{{field.name}}}, '%')</if>"
                )
            elif field.query == "eq":
                where_lines.append(
                    f"            <if test=\"{field.name} != null\"> and {field.column} = #{{{field.name}}}</if>"
                )
        where_lines.append("            <if test=\"delFlag != null and delFlag != ''\"> and del_flag = #{delFlag}</if>")
        insert_columns = "\n".join(
            f"            <if test=\"{field.name} != null\">{field.column},</if>"
            for field in spec.fields
        ) or "            <!-- TODO: columns -->"
        insert_values = "\n".join(
            f"            <if test=\"{field.name} != null\">#{{{field.name}}},</if>"
            for field in spec.fields
        ) or "            <!-- TODO: values -->"
        update_lines = "\n".join(
            f"            <if test=\"{field.name} != null\">{field.column} = #{{{field.name}}},</if>"
            for field in spec.fields
            if field.name != "id"
        ) or "            <!-- TODO: update assignments -->"
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n"
            "<!DOCTYPE mapper\n"
            "        PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\"\n"
            "        \"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">\n"
            f"<mapper namespace=\"{mapper_package}.{entity_name}Mapper\">\n\n"
            f"    <resultMap id=\"{entity_name}Result\" type=\"{domain_package}.{entity_name}\">\n"
            f"{result_map}\n"
            "    </resultMap>\n\n"
            f"    <sql id=\"select{entity_name}Vo\">\n"
            f"        select {columns} from {spec.table_name}\n"
            "    </sql>\n\n"
            f"    <select id=\"select{entity_name}ById\" parameterType=\"Long\" resultMap=\"{entity_name}Result\">\n"
            f"        <include refid=\"select{entity_name}Vo\"/>\n"
            "        where id = #{id}\n"
            "    </select>\n\n"
            f"    <select id=\"select{entity_name}List\" parameterType=\"{bo_package}.{spec.bo_name}\" resultType=\"{vo_package}.{spec.vo_name}\">\n"
            f"        <include refid=\"select{entity_name}Vo\"/>\n"
            "        <where>\n"
            f"{chr(10).join(where_lines)}\n"
            "        </where>\n"
            "    </select>\n\n"
            f"    <insert id=\"insert{entity_name}\" parameterType=\"{bo_package}.{spec.bo_name}\">\n"
            f"        insert into {spec.table_name}\n"
            "        <trim prefix=\"(\" suffix=\")\" suffixOverrides=\",\">\n"
            f"{insert_columns}\n"
            "        </trim>\n"
            "        <trim prefix=\"values (\" suffix=\")\" suffixOverrides=\",\">\n"
            f"{insert_values}\n"
            "        </trim>\n"
            "    </insert>\n\n"
            f"    <update id=\"update{entity_name}\" parameterType=\"{bo_package}.{spec.bo_name}\">\n"
            f"        update {spec.table_name}\n"
            "        <trim prefix=\"SET\" suffixOverrides=\",\">\n"
            f"{update_lines}\n"
            "        </trim>\n"
            "        where id = #{id}\n"
            "    </update>\n\n"
            f"    <delete id=\"delete{entity_name}ById\" parameterType=\"Long\">\n"
            f"        delete from {spec.table_name} where id = #{{id}}\n"
            "    </delete>\n\n"
            f"    <delete id=\"delete{entity_name}ByIds\" parameterType=\"Long\">\n"
            f"        delete from {spec.table_name} where id in\n"
            "        <foreach collection=\"array\" item=\"id\" open=\"(\" separator=\",\" close=\")\">\n"
            "            #{id}\n"
            "        </foreach>\n"
            "    </delete>\n"
            "</mapper>\n"
        )


class FeaturePlanner:
    DEFAULT_SUFFIX = "Feature"

    def infer_entity_name(self, feature_name: str, explicit_entity: str | None = None) -> str:
        if explicit_entity:
            return self._normalize_explicit_entity(explicit_entity)

        ascii_pieces = re.findall(r"[A-Za-z0-9]+", feature_name)
        if ascii_pieces:
            return "".join(piece[:1].upper() + piece[1:] for piece in ascii_pieces)

        mapped = self._map_known_feature_name(feature_name)
        if mapped:
            return mapped
        return self.DEFAULT_SUFFIX

    def _normalize_explicit_entity(self, entity_name: str) -> str:
        pieces = re.split(r"[^A-Za-z0-9]+", entity_name)
        merged = "".join(piece[:1].upper() + piece[1:] for piece in pieces if piece)
        if not merged:
            raise ValueError("Explicit entity name must contain letters or numbers.")
        return merged

    def _map_known_feature_name(self, feature_name: str) -> str | None:
        normalized = re.sub(r"\s+", "", feature_name)
        known = {
            "设备台账": "DeviceLedger",
            "设备管理": "Device",
            "灯具台账": "LampLedger",
            "用户管理": "UserProfile",
            "供应商管理": "Supplier",
        }
        return known.get(normalized)
