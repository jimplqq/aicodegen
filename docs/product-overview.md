# AI Codegen Runtime 产品概览

## 项目初衷

`aicodegen` 的初衷，是把 AI 从“理解需求”推进到“真正落地代码”这一步做得更稳定、更可复用。

在真实开发里，Agent 往往已经能理解“新增设备台账功能”“补一个 CRUD 模块”这类自然语言需求，但真正执行时，还需要继续完成很多工程化动作，例如识别项目技术栈、定位业务模块、推断包路径、准备模板、生成文件，以及为后续验证和复用保留状态。如果这些能力分散在不同 Agent 或不同脚本里，行为会不一致，维护成本也会越来越高。

`aicodegen` 希望提供一个统一的本地运行时，把这些公共能力沉淀下来，让 CLI 和支持 MCP 的 AI Agent 共用同一套项目分析、模板准备和代码生成机制。

## 产品定位

`aicodegen` 是一个**按需启动的本地 AI 代码生成运行时**。

它的定位不是通用 IDE，也不是完整低代码平台，而是一个面向真实项目目录工作的中间层工具，负责把以下几件事标准化：

- 识别当前项目的语言、框架和结构
- 生成并维护工作区级状态
- 为生成工具准备模板和上下文
- 对外提供统一的 CLI 和 MCP 调用入口
- 让不同 AI Agent 复用同一套代码生成基础设施

## 适用场景

当前版本更适合以下场景：

- 在本地业务项目中进行 AI 辅助代码生成
- 给多个 Agent 暴露统一的项目感知和代码生成入口
- 面向 Java 项目生成基础 CRUD 骨架
- 为支持 MCP 的客户端接入本地可控工具能力
- 在 RuoYi、Spring Boot、多模块项目中加速样板代码搭建

## 核心功能

### 1. 工作区初始化

通过 `init` 为目标项目创建 `.agent/` 工作区状态目录，并生成基础配置文件。

### 2. 项目检测

自动识别项目语言、构建工具、框架、测试框架、模块结构和部分工程约定。

### 3. 工作区配置生成

根据检测结果生成适合当前项目的工具配置，并支持用户覆盖语言、框架、模板目录、构建命令和测试命令。

### 4. 模板学习与复用

首次执行时从项目样例中提取模板元数据，后续优先复用已有模板，而不是重复分析。

### 5. 代码生成

当前主要面向 Java 场景，支持实体生成和 CRUD 骨架生成。

### 6. MCP 工具暴露

通过 MCP stdio server 将运行时能力暴露给外部 Agent，使其可以通过工具调用完成项目状态查询、模板准备和代码生成。

## 当前工具列表

当前已经暴露或内置的主要工具能力如下：

| 工具 / 命令 | 说明 |
| --- | --- |
| `init` | 初始化工作区，生成 `.agent/` 状态目录和基础配置 |
| `detect` | 检测项目语言、框架、构建工具和结构信息 |
| `status` | 查看当前工作区状态、模板目录和工具元数据 |
| `ensure-template` | 为指定工具准备并持久化模板元数据 |
| `generate entity` | 仅生成实体 / domain 文件 |
| `generate crud` | 生成完整 CRUD 骨架 |
| `generate feature` | 通过自然语言特征名推断实体并生成代码 |
| `project_status` | MCP 工具，返回工作区状态 |
| `ensure_template` | MCP 工具，确保模板存在 |
| `generate_entity` | MCP 工具，生成实体文件 |
| `generate_crud` | MCP 工具，生成 CRUD 骨架 |
| `generate_feature` | MCP 工具，高层特征生成入口 |

## 当前已支持的能力范围

### 项目识别

当前可识别的项目类型包括：

- Java Maven
- Java Gradle
- Node / JavaScript / TypeScript
- Python
- Go

可识别的部分框架或技术线索包括：

- Spring Boot
- RuoYi 风格结构
- React
- Next.js
- Express
- FastAPI
- Django
- Flask

### 代码生成

当前真正成熟的生成能力，主要集中在 Java CRUD 场景，尤其适合：

- Spring 风格项目
- MyBatis / MyBatis-Plus 方向项目
- RuoYi 风格后台工程

可生成的文件类型包括：

- `domain`
- `bo`
- `vo`
- `mapper`
- `service`
- `service_impl`
- `controller`
- `mapper_xml`

## 工作区状态文件

`aicodegen` 采用“程序本体与项目状态分离”的设计。程序安装一次即可，不同项目各自维护自己的 `.agent/`。

主要状态文件包括：

- `project_analysis.json`：保存项目分析结果
- `tools.json`：保存工具配置、状态和模板元数据
- `workspace_config.json`：保存工作区级覆盖配置
- `templates/`：保存学习后的模板产物

## 当前边界

为了避免误解，当前项目也有比较明确的边界：

- 检测范围比生成范围更广
- 生成能力目前主要集中在 Java 场景
- 模板生命周期虽已具备基础状态与元数据持久化，但完整验证和失败恢复还未完全闭环
- 还没有扩展成多工具、多语言的完整生成平台

## 典型使用方式

### 命令行方式

1. 在目标项目执行 `init`
2. 使用 `detect` 或 `status` 确认分析结果
3. 通过 `ensure-template` 准备模板
4. 使用 `generate feature` 或 `generate crud` 生成代码

### MCP 方式

1. 启动 `aicodegen --workspace <project> mcp`
2. 让客户端连接本地 MCP server
3. 由 Agent 调用 `project_status`、`ensure_template`、`generate_feature`

## 总结

`aicodegen` 的核心价值，不是替代开发者，而是把 AI 生成代码前后最容易分散、重复、失控的那段流程收口成一个统一运行时。这样，AI 的自然语言理解能力，才更有机会稳定转化为真实项目里的可落地代码。
