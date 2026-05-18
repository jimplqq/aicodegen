# AI Codegen Runtime

`aicodegen` 是一个按需启动的本地代码生成运行时，给 CLI 和支持 MCP 的 AI Agent 复用同一套项目分析、模板准备和代码生成能力。

它解决的是这样一类问题：

- Agent 能理解“新增设备台账功能”这类自然语言需求
- 但真正落地到项目里时，需要先识别技术栈、判断模块位置、选择模板、生成文件
- 如果每个 Agent 都各自实现一遍这些逻辑，成本高、行为也不稳定

这个项目把那部分“可复用、可验证、可持久化”的能力收口成一个独立运行时：

- 不需要常驻服务
- 在目标项目目录按需执行
- 通过 `.agent/` 保存工作区状态
- 同时支持命令行和 MCP 工具调用

## 适用场景

当前版本最适合下面的场景：

- 在本地业务项目里做 AI 辅助代码生成
- 给多个 Agent 暴露统一的“项目感知 + 代码生成”入口
- 在 Java 项目里生成基础 CRUD 骨架
- 给支持 MCP 的客户端接入一个本地可控的生成工具

如果你正在做的是 RuoYi、Spring Boot、多模块 Java 项目，这个仓库现在的能力会更贴近实际使用。

## 当前能力概览

当前仓库已经可以完成以下流程：

1. 初始化工作区
2. 检测项目语言和技术栈
3. 根据检测结果生成工作区工具配置
4. 首次学习并持久化模板元数据
5. 生成 Java 实体或 CRUD 骨架
6. 通过 MCP 以工具方式暴露这些能力

当前重点能力包括：

- 项目检测：Java / Node / Python / Go 的基础启发式识别
- 工作区初始化：生成 `.agent/` 状态目录和配置文件
- 模板准备：支持 `crud_generator` 模板首次学习与复用
- Java 代码生成：
  - `domain`
  - `bo`
  - `vo`
  - `mapper`
  - `service`
  - `service_impl`
  - `controller`
  - `mapper_xml`
- MCP 工具暴露：
  - `project_status`
  - `ensure_template`
  - `generate_entity`
  - `generate_crud`
  - `generate_feature`

## 当前边界

这部分很重要，免得 README 写得像全能工具。

目前已经实现的“检测范围”比“生成范围”更广：

- 检测支持 Java、Node、Python、Go
- 但生成能力目前主要面向 Java，尤其是 RuoYi / Spring 风格项目

换句话说：

- 你可以用它检测 Python、Node、Go 项目
- 但当前真正成熟的生成逻辑，还是 Java CRUD 方向

另外，模板生命周期虽然已经有基础状态和元数据持久化，但完整的验证、失败恢复、重试与 doctor 命令还在继续推进。

## 项目结构

```text
.
├─ docs/
│  └─ kimi-codex-mcp.md
├─ src/
│  └─ aicodegen/
│     ├─ __init__.py
│     ├─ cli.py
│     ├─ configurator.py
│     ├─ detector.py
│     ├─ generator.py
│     ├─ mcp_server.py
│     ├─ models.py
│     ├─ path_setup.py
│     ├─ runtime.py
│     ├─ storage.py
│     └─ template_manager.py
├─ tests/
│  └─ test_detector.py
├─ pyproject.toml
└─ README.md
```

核心模块说明：

- `cli.py`: 命令行入口
- `runtime.py`: 运行时编排，负责把检测、配置、模板、生成串起来
- `detector.py`: 项目技术栈识别
- `configurator.py`: 根据分析结果生成工具配置
- `template_manager.py`: 模板学习与模板元数据持久化
- `generator.py`: Java 实体和 CRUD 文件生成
- `mcp_server.py`: MCP stdio 服务入口
- `storage.py`: `.agent/` 状态目录读写
- `models.py`: 运行时使用的数据模型

## 环境要求

- Python `3.11` 或更高版本

先确认 Python 版本：

```bash
python --version
```

## 安装

### 1. 克隆仓库

```bash
git clone https://gitee.com/questiny/aicodegen.git
cd aicodegen
```

### 2. 创建虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. 开发模式安装

```bash
pip install -e .
```

安装成功后会得到一个本地命令：

```bash
aicodegen
```

## 快速开始

下面用“在一个已有业务项目目录里使用 `aicodegen`”作为示例。

### 1. 初始化工作区

```bash
aicodegen --workspace /path/to/your/project init
```

如果你在当前目录执行，可以写成：

```bash
aicodegen --workspace . init
```

初始化后会在目标项目里生成本地状态目录：

```text
.agent/
  project_analysis.json
  tools.json
  workspace_config.json
  templates/
```

`init` 的返回结果会包含：

- 工作区路径
- `.agent/` 路径
- `tools.json` 路径
- `project_analysis.json` 路径
- `workspace_config.json` 路径
- 模板根目录
- 检测值与配置值摘要

### 2. 查看识别结果

```bash
aicodegen --workspace . detect
```

这个命令会重新识别当前项目，并把识别结果写回：

```text
.agent/project_analysis.json
```

### 3. 查看运行时状态

```bash
aicodegen --workspace . status
```

这个命令会返回：

- 当前工作区是否已初始化
- 工具配置文件路径
- 分析文件路径
- 工作区配置文件路径
- 模板根目录
- 建议工具列表
- 各工具当前状态和模板元数据

### 4. 准备模板

```bash
aicodegen --workspace . ensure-template --tool crud_generator
```

首次执行时会：

- 扫描项目里的样例文件
- 为 `crud_generator` 生成模板元数据
- 把结果写入 `.agent/templates/`
- 更新工具状态

后续再次执行时会优先复用已有模板，而不是重复学习。

### 5. 生成代码

#### 只生成实体

```bash
aicodegen --workspace . generate entity --entity DeviceLedger --comment 设备台账
```

#### 生成完整 CRUD 骨架

```bash
aicodegen --workspace . generate crud --entity DeviceLedger --comment 设备台账
```

#### 通过自然语言特征名生成

```bash
aicodegen --workspace . generate feature --name 设备台账
```

如果你想明确指定实体名：

```bash
aicodegen --workspace . generate feature --name 设备台账 --entity DeviceLedger
```

如果你已经准备好了结构化规格 JSON，也可以这样：

```bash
aicodegen --workspace . generate feature --name 设备台账 --spec-file feature.json
```

## `init` 支持的参数

`init` 不只是“建目录”，它也负责生成工作区级配置。

支持的参数如下：

```bash
aicodegen --workspace . init \
  --language java \
  --framework spring-boot \
  --template-root .agent/templates \
  --build-command "mvn -q -DskipTests package" \
  --test-command "mvn -q test" \
  --force
```

参数说明：

- `--language`: 覆盖自动识别的语言
- `--framework`: 覆盖自动识别的框架
- `--template-root`: 指定模板目录，支持相对或绝对路径
- `--build-command`: 保存工作区构建命令
- `--test-command`: 保存工作区测试命令
- `--force`: 以默认配置重新初始化，再应用本次覆盖项

## 工作区状态文件说明

`aicodegen` 的一个核心设计，是把“程序本体”和“项目状态”分离。

- 程序本体只需要安装一次
- 每个项目目录维护自己的 `.agent/`

`.agent/` 中的主要文件：

### `project_analysis.json`

保存当前项目的分析结果，例如：

- 语言
- 构建工具
- 框架
- 测试框架
- 包管理器
- 架构类型
- 模块列表
- 基础包名

### `tools.json`

保存运行时工具配置和工具状态，例如：

- 建议启用的工具
- `crud_generator` 的模块和包路径配置
- 每个工具的生命周期状态
- 模板相关元数据

### `workspace_config.json`

保存用户可控的工作区配置，例如：

- 模板根目录
- 语言/框架覆盖
- 构建命令
- 校验命令
- 生成默认值
- Agent 集成提示

### `templates/`

保存首次模板学习后的结构化结果。

## 当前支持的项目识别

### Java

通过以下文件识别：

- `pom.xml`
- `build.gradle`
- `build.gradle.kts`

可推断的信息包括：

- Maven / Gradle
- Spring Boot
- JUnit / JUnit 5
- MyBatis / MyBatis-Plus / JPA
- 模块结构
- 基础包名
- 是否存在 `Mapper.xml`
- 是否属于 RuoYi 风格项目

### Node

通过 `package.json` 做基础识别，可判断：

- `javascript` / `typescript`
- `react`
- `nextjs`
- `express`
- `jest`
- `vitest`

### Python

通过 `pyproject.toml` 或 `requirements.txt` 做基础识别，可判断：

- `python`
- `fastapi`
- `django`
- `flask`
- `pytest`

### Go

通过 `go.mod` 做基础识别。

## 当前生成逻辑说明

当前生成器最主要的目标是 Java CRUD 骨架生成。

在配置完整时，`crud_generator` 会生成：

- `domain`
- `bo`
- `vo`
- `mapper`
- `service`
- `service_impl`
- `controller`
- `mapper_xml`

对 RuoYi 风格项目，运行时会尽量从分析结果中推断：

- 业务模块名
- controller 包
- service 包
- mapper 包
- domain 包
- mapper xml 路径
- 返回包装类型
- controller / entity 基类

## MCP 集成

如果你的 Agent 或客户端支持 MCP，可以直接把 `aicodegen` 暴露为本地 MCP server。

### 启动 MCP 服务

PowerShell：

```powershell
aicodegen --workspace C:\workspace\your-project mcp
```

Git Bash：

```bash
aicodegen --workspace /c/workspace/your-project mcp
```

### 当前暴露的 MCP 工具

- `project_status`
- `ensure_template`
- `generate_entity`
- `generate_crud`
- `generate_feature`

### 推荐调用顺序

当用户说“新增设备台账功能”“生成 CRUD”“补一个后台模块骨架”时，推荐 Agent 这样调用：

1. `project_status`
2. 必要时调用 `ensure_template`
3. 调用 `generate_feature`

### MCP 配置示例

```json
{
  "mcpServers": {
    "ai-codegen-demo": {
      "command": "aicodegen",
      "args": [
        "--workspace",
        "C:\\workspace\\your-project",
        "mcp"
      ]
    }
  }
}
```

更多 MCP 接入说明见：

- [docs/kimi-codex-mcp.md](docs/kimi-codex-mcp.md)

## 示例工作流

下面是一条比较自然的日常使用路径：

### 场景一：你自己在命令行里使用

```bash
aicodegen --workspace . init
aicodegen --workspace . detect
aicodegen --workspace . ensure-template --tool crud_generator
aicodegen --workspace . generate feature --name 设备台账
```

### 场景二：让 MCP Agent 帮你生成

1. 启动 `aicodegen --workspace <project> mcp`
2. 让客户端连接本地 MCP server
3. 用户说一句自然语言需求，例如：

```text
新增设备台账功能
```

4. Agent 通过 `generate_feature` 完成生成

## 测试

运行单元测试：

```bash
python -m unittest tests.test_detector -q
```

如果你想先做语法层检查：

```bash
python -m compileall src\aicodegen
```

## 当前已知限制

- 生成逻辑目前主要面向 Java，尤其是 RuoYi / Spring 类项目
- 模板验证与失败恢复还没有完全打通
- 还没有独立的 doctor 命令
- 还没有多种生成工具的完整注册中心
- 还没有覆盖更多框架的专用模板体系

## 后续方向

接下来值得继续补强的点包括：

1. 模板验证阶段和失败恢复流程
2. doctor / diagnose 类命令
3. 更清晰的工具生命周期管理
4. 更多框架和项目结构的模板支持
5. 更完整的 MCP 协议与使用说明

## 许可证

项目当前包含 [LICENSE](LICENSE) 文件，请按仓库中的许可证内容使用。
