# Fancy Agent

一个全栈 AI Agent 平台。支持配置 LLM、MCP 服务器，并将它们组合成 Agent 进行流式对话，同时内置独立的图像生成工作台。

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
- **图像生成工作台** — 支持 DALL-E、Stability AI、SiliconFlow 等多个供应商
- **文件上传与解析** — 支持 PDF、DOCX、TXT、CSV、JSON 等格式内联到消息
- **定时任务** — 配置 daily/weekly/monthly 定时任务，结果可通过邮件发送
- **邮件 Agent** — 轮询邮箱，将邮件路由到指定 Agent 处理
- **Prompt 模板** — 管理可复用的提示词片段，支持分类与一键复制
- **Token 用量统计** — 查看总量、按 Agent 分组及最近 30 天每日趋势
- **JWT 鉴权** — Access Token (365天) + httpOnly Refresh Token (3650天)

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

所有服务容器化，推荐用于服务器部署。

**首次部署**

```bash
# 1. 配置环境变量
cp backend/.env.docker.example backend/.env
# 编辑 backend/.env，至少修改 SECRET_KEY 为随机字符串

# 2. 生成 requirements.txt（Docker 镜像构建依赖此文件）
cd backend && uv export --no-hashes --format requirements-txt -o requirements.txt && cd ..

# 3. 构建前端静态文件
cd frontend && npm install && npm run build && cd ..

# 4. 启动容器
docker compose up --build -d
```

启动完成后访问 `http://your-server-ip`，注册账号即可使用。

**后续更新**

```bash
bash deploy.sh
```

`deploy.sh` 自动完成：拉取最新代码 → 覆盖 `.env`（从 `backend/.env.prd`）→ 构建前端 → 重启容器。服务器上需提前创建 `backend/.env.prd`。

> `uv export` 会自动为 Windows 专属包（如 `pywin32`）添加 `; sys_platform == "win32"` 标记，确保 Linux 镜像构建时跳过它们。

## 环境变量

后端读取 `backend/.env`（所有后端命令须在 `backend/` 目录下执行，否则 `.env` 不会加载）：

| 变量 | 必填 | 说明 |
|---|---|---|
| `DATABASE_URL` | ✅ | SQLite：`sqlite+aiosqlite:///./fancy_agent.db`；MySQL：`mysql+asyncmy://user:pass@host/db` |
| `SECRET_KEY` | ✅ | JWT 签名密钥，**必须设置为随机字符串，修改后所有已登录会话失效** |
| `OSS_URL` | ✅ | 上传文件的访问基础 URL，本地开发填 `http://localhost:8000` |
| `UPLOAD_DIR` | ✅ | 文件上传存储目录，如 `./data/uploads` |
| `WORKSPACE_DIR` | ✅ | Agent 工作区目录，如 `./data/workspaces` |
| `SEARCH_PROVIDER` | — | `duckduckgo`（默认）或 `tavily` |
| `TAVILY_API_KEY` | — | `SEARCH_PROVIDER=tavily` 时必填 |
| `EMAIL_ENABLED` | — | 是否启用邮件 Agent（`true` / `false`，默认 `false`） |
| `EMAIL_PROVIDER` | — | `gmail` / `163` / `qq` / `outlook` |
| `EMAIL_ADDRESS` | — | 邮箱地址 |
| `EMAIL_PASSWORD` | — | 邮箱密码（Gmail 需用应用专用密码） |

前端读取 `frontend/.env.development` / `frontend/.env.production`：

| 变量 | 说明 |
|---|---|
| `VITE_API_BASE` | 后端 API 地址，如 `http://localhost:8000` |

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

### 同步 API 类型

修改后端 Schema 后，重新生成前端类型：

```bash
# 1. 确保后端正在运行，导出 openapi.json
# 2. 执行生成命令
cd frontend
npx openapi-typescript-codegen --input ./openapi.json --output src/api --client axios
```

> 若后端无法启动（如无数据库），可手动在 `src/api/models/` 下添加类型文件，在 `src/api/services/` 下添加 Service 类，并在 `src/api/index.ts` 中导出。

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
