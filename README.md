# Fancy Agent

[English](./README_EN.md) | 中文

一个全栈 AI Agent 平台。支持配置 LLM、MCP 服务器，并将它们组合成 Agent 进行流式对话，同时内置独立的图像生成工作台。

## 演示

- Bilibili: [我做了一个全栈 AI Agent 平台：支持 MCP、HTTP API 工具、图像工作台](https://www.bilibili.com/video/BV1MVJn69EPP/?share_source=copy_web&vd_source=f74e0c665f4fb75caa2057a3e0d75600)

![工作区与图像工作台演示](docs/assets/workspace-image-studio-demo.gif)

## 项目背景

这是一个个人练手项目，在折腾各种 AI 工具的过程中攒出来的。

### 为什么做这个

现在的 AI 产品大致分两类：一类是 ChatGPT / Grok / Claude 这样的传统 chatbot，另一类是 Claude Code / Codex 这样深度嵌入开发环境的本地 harness。这个项目想做介于两者之间的东西——有 chatbot 的易用性，但又比 chatbot 更透明、更可控。

具体来说，用现有 chatbot 做 agent 时有几个痛点：

- **黑盒**：不知道系统提示词怎么写的、内置了哪些工具、工具的行为逻辑是什么，出了问题很难排查
- **无法自定义工具**：想接入自己的业务接口或内部 API，基本没有办法
- **订阅墙**：非付费用户有附件上传次数、消息条数等各种限制，用自己的 API Key 反而要绕一圈

### 这个项目能做什么

- **完全透明的 agent 配置**：系统提示词、绑定的工具、调用上限一目了然，自己写自己改
- **HTTP API 工具**：这是本项目的核心亮点之一。大部分 MCP 工具本质上只是对某个接口的封装，本项目直接支持将任意 HTTP API 配置成工具供 AI 调用，不需要写 MCP server，配个 URL 和参数就能用
- **用自己的 API Key**：原生支持 OpenAI、Anthropic、Google Gemini、Ollama（本地）四种协议；硅基流动、阿里云、DeepSeek 等任意 OpenAI 兼容接口可通过自定义 `base_url` 接入，不受平台订阅限制
- **本地自用或对外发布**：SQLite 零依赖跑本地，Docker Compose 一键部署到服务器对外提供服务
- **扩展能力**：Webhook 触发（需公网 IP）、邮件提醒、定时任务，适合做一些轻量自动化

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI (Python 3.12) · 异步 SQLAlchemy + MySQL · LangChain / LangGraph · MCP Adapter |
| 前端 | React 19 · TypeScript · Vite · Tailwind CSS v4 |
| 基础设施 | Docker Compose (MySQL + FastAPI + Nginx) |

## 功能特性

- **Agent 编排** — 自由组合 LLM + MCP 工具 + 自定义 HTTP API 工具
- **流式对话** — SSE 实时输出，支持分支消息树
- **Human-in-the-loop** — 工具调用前可暂停等待用户审批
- **会话工作区** — 每个会话拥有独立的文件沙箱目录，Agent 可在其中读写文件（代码、数据、报告等），生成的文件会实时出现在侧边栏，支持单文件下载或打包下载全部；代码执行沙箱与工作区打通，脚本产物直接落盘可见
- **图像生成工作台** — 支持 DALL-E、Stability AI、SiliconFlow 等多个供应商
- **文件上传与解析** — 支持 PDF、DOCX、TXT、CSV、JSON 等格式内联到消息
- **定时任务** — 配置 daily/weekly/monthly 定时任务，结果可通过邮件发送
- **邮件 Agent** — 轮询邮箱，将邮件路由到指定 Agent 处理
- **Prompt 模板** — 管理可复用的提示词片段，支持分类与一键复制
- **Token 用量统计** — 查看总量、按 Agent 分组及最近 30 天每日趋势
- **JWT 鉴权** — Access Token

## 内置工具

除了自定义的 MCP / HTTP API 工具，平台还预置了一批开箱即用的工具，在创建 Agent 时勾选即可绑定：

| 工具 | 说明 |
|---|---|
| `web_search` | 联网搜索（DuckDuckGo / Tavily） |
| `web_fetch` | 抓取指定网页并提取正文 |
| `python_exec` | 隔离子进程沙箱里执行 Python 代码（白名单导入、受限文件访问） |
| `workspace` | 读写当前会话的文件工作区，产物自动出现在侧边栏 |
| `scheduled_task_manager` | 让 Agent 自己创建/管理定时任务 |
| `skill_manager` | 按需拉取技能（SKILL.md + 附带脚本）并在工作区运行 |
| `memory_manager` | 读写用户长期记忆（core 记忆会自动注入系统提示词） |
| `prompt_template_manager` | 查询可复用的提示词模板 |
| `knowledge_graph_manager` | 抽取/查询知识图谱节点与关系 |
| `help_document_manager` | 查询内置帮助文档 |

> **关于联网搜索**：`web_search` 可选 DuckDuckGo（默认）或 Tavily（`SEARCH_PROVIDER=tavily`，需 API Key）。国内网络环境下两者通常都需要科学上网；但在阿里云等国内服务器上实测 **Tavily 可直接访问，DuckDuckGo 不行**。部署在国内服务器时建议改用 Tavily。

## 部署方式

### 方式一：本地开发（SQLite，零依赖）

最简单的上手方式，无需安装数据库。

**后端**

```bash
cd backend
cp .env.sqlite.example .env
uv sync
uv run uvicorn app.main:app --reload
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

前端默认访问 `http://localhost:5173`，API 指向 `http://localhost:8000`。

---

### 方式二：本地 MySQL（前后端分离调试）

适合需要真实数据库环境、或调试 MySQL 特有行为的场景。需要本地已启动 MySQL 8.0+ 并创建好数据库。

```sql
CREATE DATABASE fancy_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**后端**

```bash
cd backend
cp .env.mysql.example .env
# 编辑 .env，填入正确的 MySQL 连接信息
uv sync
uv run uvicorn app.main:app --reload
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

---

### 方式三：生产部署（Docker Compose）

所有服务容器化（MySQL + FastAPI + 代码沙箱 + Nginx），推荐用于服务器部署。

**首次部署**

```bash
# 1. 复制并填写集中配置（唯一需要手动维护的文件）
cp deploy.config.example deploy.config
```

打开 `deploy.config`，**至少填写以下三项**，其余保持默认即可：

| 变量 | 说明 |
|---|---|
| `PUBLIC_HOST` | 服务器实际地址，如 `http://your-server-ip`，无结尾斜杠 |
| `DB_PASSWORD` | MySQL root 密码，自定义任意字符串即可 |
| `SECRET_KEY` | JWT 签名密钥，建议随机字符串（`openssl rand -hex 32`） |

```bash
# 2. 运行配置渲染脚本（自动生成 backend/.env 等配置文件）
bash configure.sh

# 3. 构建前端静态文件
cd frontend && npm install && npm run build && cd ..

# 4. （依赖有变更时）重新生成 requirements.txt
# cd backend && uv export --no-hashes --format requirements-txt -o requirements.txt && cd ..

# 5. 启动所有容器
docker compose up --build -d
```

启动完成后访问 `http://your-server-ip`，注册账号即可使用。

> **注意**：首次启动会拉取 MySQL 8.0 / Python 3.12-slim 等基础镜像，国内服务器建议提前配置 Docker 镜像加速（Docker Desktop → Settings → Docker Engine 中添加 `registry-mirrors`）。

> **前端不需要改任何配置**：前端生产构建使用相对路径访问 API，nginx 保证同源，换域名/IP 不需要重新构建前端。

**后续更新**

```bash
bash deploy.sh
```

`deploy.sh` 自动完成：拉取最新代码 → 调用 `configure.sh` 渲染配置 → 构建前端 → 重启容器。`deploy.config` 已被 `.gitignore` 忽略，`git reset` 不会清除它，一次配置后长期有效。换服务器/域名只需修改 `deploy.config` 里的 `PUBLIC_HOST`。

> `uv export` 会自动为 Windows 专属包（如 `pywin32`）添加 `; sys_platform == "win32"` 标记，确保 Linux 镜像构建时跳过它们。

## 快速上手

服务跑起来后，按下面的流程配置出你的第一个 Agent：

1. **注册 / 登录** — 打开首页注册账号，登录后进入主界面。
2. **配置 LLM 模型** — 在「模型」页新增一个 LLM，选择提供商（OpenAI / Anthropic / Google / Ollama），填入 `model_name`、`api_key`，以及可选的 `base_url`。硅基流动、阿里云、DeepSeek 等 OpenAI 兼容服务选 `OpenAI` 并改写 `base_url` 即可接入；本地 Ollama 选 `Ollama`、把 `base_url` 指向 `http://<host>:11434`（无需 API Key）。

   > 模型层基于 LangChain 的 `init_chat_model` 封装，不同提供商的消息格式会自动统一，业务层无需关心差异。要新增其他提供商：后端用 `uv`/`pip` 装上对应的 `langchain-xxx` 集成包，再在前端「模型」表单的提供商下拉（`frontend/src/components/LLMForm.tsx`）里放出该选项即可。
3. **（可选）准备工具** — 需要外部能力时，先配置工具：
   - **MCP** — 粘贴 Claude Desktop 格式的 MCP 配置即可导入
   - **HTTP API 工具** — 通过向导把任意 REST 接口封装成工具（URL、方法、参数、响应提取四步）
   - **图像工具** — 接入图像生成供应商
4. **创建 Agent** — 在「助手」页新建 Agent：选择 LLM、写系统提示词、勾选要绑定的工具（MCP / API 工具 / 内置工具），可选开启 Human-in-the-loop 审批。
5. **开始对话** — 进入聊天页，选中 Agent 即可流式对话，支持上传文件、查看工具调用、分支重生成。

## Bot / Webhook 接入

平台支持把 Agent 接到外部入站 Webhook，被外部事件或聊天机器人触发。入站 Webhook 端点是**公开的（无需登录）**，按通道各自做签名 / 令牌校验；**在 Webhook 上下文中 Human-in-the-loop 审批会自动跳过**（无法人工介入，直接执行）。所有通道都需要服务有**公网可访问地址**。

> 当前验证状态：
> - 钉钉：已在真实环境中验证通过
> - Telegram：受公网 HTTPS 等条件限制，代码已实现并补充了接入文档，但作者本人未完成实际联调验证
> - Discord：受公网 HTTPS 等条件限制，代码已实现并补充了接入文档，但作者本人未完成实际联调验证

| 通道 | 端点 | 必填凭证 | 校验方式 |
|---|---|---|---|
| 通用 HTTP | `/api/v1/webhooks/{slug}` | 自动生成 secret | HMAC-SHA256（`X-Signature` 头） |
| Telegram | `/api/v1/telegram/webhooks/{slug}` | Bot Token | `x-telegram-bot-api-secret-token` 头 |
| 钉钉 | `/api/v1/dingtalk/webhooks/{slug}` | App Secret | HMAC-SHA256 + 时间戳 |
| Discord | `/api/v1/discord/interactions/{slug}` | Public Key | Ed25519 签名 |

在「入站 Webhook」页选择对应通道并填入凭证后，系统会生成正式 URL（和内部 secret）。

**通用 HTTP Webhook** — 最简单，适合从自己的脚本/系统触发 Agent。请求体：

```json
{ "content": "要发给 Agent 的消息", "metadata": {} }
```

请求需带 `X-Signature: sha256=<HMAC>` 头，签名为 `HMAC-SHA256(secret, 原始请求体)`。响应返回 `session_id`、`message_id` 和 Agent 回复 `content`。

**聊天机器人通道** — 详细的平台侧配置步骤见各自文档：

- 钉钉：[docs/dingtalk-webhook-setup.md](docs/dingtalk-webhook-setup.md)
- Telegram：[docs/telegram-webhook-setup.md](docs/telegram-webhook-setup.md)
- Discord：[docs/discord-webhook-setup.md](docs/discord-webhook-setup.md)

其中钉钉文档对应的是已实测跑通的链路；Telegram 与 Discord 文档目前属于基于官方接入流程和代码实现整理的操作说明，尚未在作者当前部署条件下完成端到端实测。

## 环境变量

后端读取 `backend/.env`（所有后端命令须在 `backend/` 目录下执行，否则 `.env` 不会加载）：

| 变量 | 必填 | 说明 |
|---|---|---|
| `DATABASE_URL` | ✅ | SQLite：`sqlite+aiosqlite:///./fancy_agent.db`；MySQL：`mysql+asyncmy://user:pass@host/db` |
| `SECRET_KEY` | — | JWT 签名密钥，有默认值（`super-secret-key`），不设置也能启动；生产环境务必改为随机字符串，修改后所有已登录会话失效 |
| `OSS_URL` | ✅ | 上传文件的访问基础 URL，本地开发填 `http://localhost:8000` |
| `UPLOAD_DIR` | ✅ | 文件上传存储目录，如 `./data/uploads` |
| `WORKSPACE_DIR` | ✅ | Agent 工作区目录，如 `./data/workspaces` |
| `SEARCH_PROVIDER` | — | `duckduckgo`（默认）或 `tavily` |
| `TAVILY_API_KEY` | — | `SEARCH_PROVIDER=tavily` 时必填 |
| `EMAIL_ENABLED` | — | 是否启用邮件 Agent（`true` / `false`，默认 `false`） |
| `EMAIL_PROVIDER` | — | `gmail` / `163` / `qq` / `outlook`（目前仅实测过 `163`，**推荐使用 163**，其余未验证） |
| `EMAIL_ADDRESS` | — | 邮箱地址 |
| `EMAIL_PASSWORD` | — | 邮箱密码（Gmail 需用应用专用密码） |

前端读取 `frontend/.env.development` / `frontend/.env.production`：

| 变量 | 说明 |
|---|---|
| `VITE_API_BASE` | 后端 API 地址。本地开发（`.env.development`）填 `http://localhost:8000`；生产构建（`.env.production`）留空，前端走相对路径，nginx 同源路由 |

## 测试

后端测试套件使用 pytest + pytest-asyncio，**无需启动数据库**（集成测试使用 SQLite 内存库）。

```bash
cd backend
uv run pytest              # 运行所有测试
uv run pytest tests/unit   # 只跑单元测试
uv run pytest tests/integration  # 只跑集成测试
uv run pytest -v           # 显示每条测试结果
```

### 测试结构

```
backend/tests/
├── conftest.py              # 共享 fixture（内存 SQLite 引擎 + Session）
├── unit/
│   ├── test_compress_util.py    # _extract_text 纯函数
│   ├── test_message_processor.py # MessageConverter / MessageProcessor
│   ├── test_schemas.py          # ValidChatModel / ValidAgent Pydantic 校验
│   └── test_security.py         # JWT 生成与解析
└── integration/
    ├── test_base_mapper.py      # BaseMapper 通用 CRUD
    └── test_agent_service.py    # AgentService 业务逻辑
```

- **单元测试** — 纯 Python，不依赖数据库，直接 `import` 被测模块即可运行
- **集成测试** — 使用 `conftest.py` 中的 `async_session` fixture，每个测试独享一个内存 SQLite 实例，测试结束自动回滚，互不干扰

### 添加新测试

集成测试直接接收 `async_session: AsyncSession` fixture，无需手动创建 session：

```python
class TestFooService:
    async def test_create(self, async_session: AsyncSession):
        service = FooService(async_session)
        result = await service.create({"name": "bar"})
        assert result.name == "bar"
```

如果新增了 Model，需在 `conftest.py` 顶部添加对应的 import，否则 `create_all` 不会建表：

```python
from app.models.foo import Foo  # noqa: F401
```

## 开发指南

### 提交规范

当前仓库的 `master` 分支已开启保护，不能直接推送。提交代码请使用以下流程：

```bash
git switch -c your-branch-name
git add .
git commit -m "type: short description"
git push -u origin your-branch-name
```

然后在 GitHub 上创建 PR，将分支合并回 `master`。

### 后端架构

```
Routers (app/api/)
  └─ Services (app/services/)
       └─ Mappers (app/mappers/)
            └─ Models (app/models/)
```

- **Routers** — HTTP / SSE 处理，依赖注入，调用 Service
- **Services** — 业务逻辑，通过构造函数接收 `AsyncSession`
- **Mappers** — 继承 `BaseMapper[T]`，提供通用 CRUD；自定义查询逻辑写在子类
- **Models** — SQLAlchemy ORM，继承 `Base` + `TimestampMixin`

新增资源时按顺序创建：`model` → `schema` → `mapper` → `service` → `router` → 注册到 `deps/service.py` 和 `main.py`，并在 `init_db()` 中 import 模型。

## 项目结构

```
fancy_agent/
├── backend/
│   ├── app/
│   │   ├── api/          # 路由层
│   │   ├── core/         # 配置、数据库、安全、调度器
│   │   ├── deps/         # FastAPI 依赖注入工厂
│   │   ├── mappers/      # 数据访问层
│   │   ├── models/       # ORM 模型
│   │   ├── schemas/      # Pydantic Schema
│   │   ├── services/     # 业务逻辑层
│   │   └── utils/        # LangChain 工具、图像适配器等
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── api/          # 自动生成的 API 客户端
    │   ├── components/   # 通用组件
    │   ├── context/      # 全局状态
    │   ├── hooks/        # 自定义 Hook
    │   └── pages/        # 页面组件
    └── package.json
```

## 更多文档

`docs/` 目录下的专题文档：

| 文档 | 说明 |
|---|---|
| [dingtalk-webhook-setup.md](docs/dingtalk-webhook-setup.md) | 钉钉 Bot 接入完整步骤与排障 |
| [telegram-webhook-setup.md](docs/telegram-webhook-setup.md) | Telegram Bot 接入完整步骤与排障 |
| [discord-webhook-setup.md](docs/discord-webhook-setup.md) | Discord 斜杠命令接入完整步骤与排障 |
| [sandbox-architecture.md](docs/sandbox-architecture.md) | 代码执行沙箱的安全架构与设计 |
| [local-limitations.md](docs/local-limitations.md) | SQLite 与 MySQL 的功能差异及取舍 |
| [项目结构说明.md](docs/项目结构说明.md) | 项目目录结构详解 |
| [stream-interrupt-persist-bug.md](docs/stream-interrupt-persist-bug.md) | 流式中断持久化问题的复盘记录 |
| [webhook-smoke-test.md](docs/webhook-smoke-test.md) | Webhook 冒烟测试记录 |
