# AI Codegen Runtime

一个供多个 AI Agent 共享调用的本地 AI 代码生成运行时。

它的目标不是让每个 Agent 都各自实现一套代码生成逻辑，而是提供一个统一的、按需启动的工具程序，用来：

- 识别当前项目的开发语言和主要技术栈
- 在项目目录下持久化分析结果和工具状态
- 为后续模板生成、调试验证和代码生成提供统一入口
- 同时支持 CLI 使用方式和 MCP 接入方式

## 当前状态

当前仓库已经包含第一批可运行骨架：

- OpenSpec 变更提案与规范
- Python 包结构
- `aicodegen` CLI 入口
- 工作区初始化
- 项目技术栈启发式识别
- `.agent/` 本地状态持久化

还未完成的部分包括：

- ToolRegistry 与工具生命周期
- 模板生成 / 调试 / 验证流程
- 完整 MCP 协议支持
- 具体生成工具，例如 CRUD generator

## 环境要求

- Python 3.11 或更高版本

先确认版本：

```bash
python --version
```

## 克隆后如何使用

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd <repo-name>
```

### 2. 创建虚拟环境

Windows PowerShell:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. 以开发模式安装

```bash
pip install -e .
```

安装完成后，本地会得到一个命令：

```bash
aicodegen
```

## 基本命令

### 初始化当前工作区

```bash
aicodegen --workspace . init
```

这会在当前项目下创建：

```text
.agent/
  tools.json
  tools/
```

### 检测当前项目技术栈

```bash
aicodegen --workspace . detect
```

这会输出识别结果，并写入：

```text
.agent/project_analysis.json
```

### 查看当前状态

```bash
aicodegen --workspace . status
```

### 以 MCP 入口启动

```bash
aicodegen --workspace . mcp
```

目前这个命令还是占位实现，用来预留后续 MCP stdio 协议接入。

## 如何验证安装成功

### 方式 1：运行单元测试

如果你是从源码运行而不是安装命令，也可以这样：

```bash
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
```

Windows 以外可以改成：

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

### 方式 2：直接跑 CLI

```bash
aicodegen --workspace . init
aicodegen --workspace . detect
aicodegen --workspace . status
```

预期结果：

- `init` 成功创建 `.agent/`
- `detect` 成功输出语言和技术栈
- `status` 成功返回工作区状态

### 方式 3：检查生成文件

确认以下文件存在：

```text
.agent/tools.json
.agent/project_analysis.json
```

## 当前支持的识别线索

当前使用启发式规则识别常见项目：

- `pom.xml` -> Java / Maven
- `build.gradle` / `build.gradle.kts` -> Java / Gradle
- `package.json` -> JavaScript / TypeScript / Node
- `pyproject.toml` / `requirements.txt` -> Python
- `go.mod` -> Go

框架识别目前支持基础判断，例如：

- Spring Boot
- FastAPI
- Django
- Flask
- React
- Next.js
- Express
- Gin

这部分后续会继续增强。

## 目录结构

```text
src/
  aicodegen/
    cli.py
    detector.py
    runtime.py
    storage.py
    mcp_server.py
tests/
openspec/
```

## OpenSpec

本次能力规划已写入 OpenSpec：

- [proposal.md](openspec/changes/add-shared-on-demand-codegen-runtime/proposal.md)
- [tasks.json](openspec/changes/add-shared-on-demand-codegen-runtime/tasks.json)
- [spec-delta.md](openspec/changes/add-shared-on-demand-codegen-runtime/specs/ai-codegen-runtime/spec-delta.md)

变更 ID：

```text
add-shared-on-demand-codegen-runtime
```

## 适合的使用方式

这个工具推荐这样使用：

1. 全局或源码安装 `aicodegen`
2. 在某个业务项目目录执行 `init`
3. 执行 `detect` 识别项目语言和技术栈
4. 后续由 CLI 或 Agent 调用统一运行时

重点是：

- 程序本体只安装一次
- 每个项目各自维护 `.agent/` 状态
- 不要求常驻后台服务
- 需要时启动，用完退出

## 下一步开发方向

接下来建议优先实现：

1. ToolRegistry 和工具状态机
2. 模板目录与模板生命周期
3. 调试验证循环
4. MCP 标准协议接入
5. 示例生成工具

## 许可证

暂未指定。
