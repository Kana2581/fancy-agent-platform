# 本地部署功能限制说明

本文说明在不同部署场景下，Fancy Agent 的哪些功能会受限或需要额外配置。

限制来自两个独立维度，不要混淆：

- **有无公网 IP / 域名**：影响需要外部平台回调的功能
- **本地进程 vs Docker**：影响文件数据的持久化

---

## 功能一览

| 功能 | 无公网 IP | 本地进程 | Docker（未配 named volume） |
|------|-----------|----------|-----------------------------|
| 核心对话 / Agent | ✅ 正常 | ✅ 正常 | ✅ 正常 |
| Webhook（Discord / 钉钉 / GitHub 等） | ❌ 不可用 | ⚠️ 需公网 | ⚠️ 需公网 |
| 图片生成（DALL-E / Stability 等） | ✅ 仅需出网 | ✅ 仅需出网 | ✅ 仅需出网 |
| Web 搜索（DuckDuckGo） | ✅ 仅需出网 | ✅ 仅需出网 | ✅ 仅需出网 |
| Web 搜索（Tavily） | ✅ 仅需出网 | ✅ 仅需出网 | ✅ 仅需出网 |
| 邮件助手 | ✅ 仅需出网 | ✅ 正常 | ✅ 正常 |
| Python 代码执行 | ✅ 正常 | ✅ 正常（并发限制 2） | ✅ 正常（并发限制 2） |
| Workspace 文件 | ✅ 正常 | ✅ 正常 | ⚠️ 重建容器丢文件 |
| MCP 服务器 | 视实现而定 | 视实现而定 | 视实现而定 |
| Help Docs 种子数据 | ✅ 正常 | ⚠️ 需手动导入 | ⚠️ 需手动导入 |

---

## 需要公网 IP 的功能

### Webhook（❌ 无公网不可用）

Discord、钉钉、GitHub 等平台收到用户消息后，会主动向你配置的回调地址发 POST 请求。如果你的服务部署在本地内网，外部平台无法访问到它，Webhook Agent 功能完全失效。

**临时方案：内网穿透**

可以用 [ngrok](https://ngrok.com/) 或 [frp](https://github.com/fatedier/frp) 将本地端口暴露到公网：

```bash
ngrok http 8000
```

拿到 ngrok 生成的公网地址后，填入对应平台的 Webhook 回调配置即可。注意 ngrok 免费版每次重启地址会变。

**附加行为：Webhook 上下文下 HITL 会被跳过**

当请求来自 Webhook（而非用户直接聊天），Agent 的"人工审批工具调用"（Human-in-the-loop）功能会被自动跳过，即遇到需要审批的工具调用时，Agent 直接中断，不会挂起等待。这是设计行为，避免 Webhook 流程永久挂起。

---

## 需要出站网络（不需要公网 IP）的功能

### 图片生成（⚠️ 需 API Key + 出网）

图片生成调用的是外部 AI 服务，只需要你的服务器能访问对应 API，不需要对方能回调你。

支持的提供商：

| 提供商 | 所需配置 |
|--------|----------|
| OpenAI（DALL-E 2 / 3） | `api_key`，可选 `base_url` |
| Stability AI | `api_key` |
| SiliconFlow | `api_key` + `base_url` |
| Aliyun | `api_key` + 区域配置 |

没有 API Key 时，图片生成功能不可用。但图片展示和上传（把图片发给 Agent）不受影响，始终可用。

### Web 搜索（⚠️ 断网不可用）

- **DuckDuckGo**（默认）：无需 API Key，能上网即可使用，结果精度有限
- **Tavily**：搜索质量更好，需要在 `.env` 中配置 `TAVILY_API_KEY`

切换方式：

```env
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-xxxxxxxx
```

不配置则自动回落到 DuckDuckGo。

### 邮件助手（⚠️ 需 SMTP / IMAP 凭证）

邮件功能本地和生产均支持，只要你有可用的邮件账号。系统用**单个共享邮箱**收发信，按发件人地址匹配注册用户。

推荐用 `EMAIL_PROVIDER` 预设：只填服务商 + 凭据，IMAP/SMTP 主机、端口、加密方式自动带出。内置预设：`gmail`、`163`、`qq`、`outlook`。

**Gmail 示例**：

```env
EMAIL_ENABLED=true
EMAIL_PROVIDER=gmail
EMAIL_ADDRESS=you@gmail.com
EMAIL_USERNAME=you@gmail.com
EMAIL_PASSWORD=你的16位应用专用密码
# 主机/端口/加密方式由 EMAIL_PROVIDER=gmail 自动带出，无需再填
```

Gmail **必须用「应用专用密码」**（不能用登录密码）：

1. 开启 Google 账号两步验证（2FA）。
2. 访问 Google 账号 → 安全性 → 「应用专用密码」（App passwords）。
3. 生成一个 16 位密码，去掉空格后填入 `EMAIL_PASSWORD`。

**163 示例**：

```env
EMAIL_ENABLED=true
EMAIL_PROVIDER=163
EMAIL_ADDRESS=you@163.com
EMAIL_USERNAME=you@163.com
EMAIL_PASSWORD=163客户端授权码
```

> 已有的 163/QQ 部署（显式 `EMAIL_IMAP_HOST`/`EMAIL_SMTP_*`、未设 `EMAIL_PROVIDER`）无需改动：加密方式按端口推断（465→SSL），IMAP ID 命令按主机名（含 `163`/`qq`）自动启用。建议仍补上 `EMAIL_PROVIDER=163` 让配置更直观。

**自定义服务商 / 覆盖预设**：任意 `EMAIL_*` 显式值都优先于预设。可手动设：

```env
EMAIL_IMAP_HOST / EMAIL_IMAP_PORT
EMAIL_SMTP_HOST / EMAIL_SMTP_PORT
EMAIL_SMTP_SECURITY=ssl        # 隐式 SSL(通常 465) 或 starttls(通常 587)；不填则按端口推断
EMAIL_IMAP_ID=true             # 163/QQ 收信必需；不填则取预设值
```

`EMAIL_ENABLED=false`（默认）时，邮件轮询不启动，调度任务的执行结果也不会通过邮件推送。

---

## 本地 vs Docker 的差异

### Workspace 文件持久化（⚠️ Docker 需配 named volume）

在 Docker 部署时，如果没有把 upload 和 workspace 目录挂载到宿主机或 named volume，每次执行 `docker compose down` 再 `up --build` 都会清空这些目录。

清空后，数据库里的文件记录仍然存在，但文件本体已经不见了，Agent workspace 里的文件无法下载，会返回 404。

`docker-compose.yml` 中需要保留以下 named volume 配置：

```yaml
volumes:
  uploads:
  workspaces:
```

本地直接运行后端进程没有这个风险，文件存在本地文件系统里，不会被意外清空。

---

## 行为差异（不影响可用性）

### Python 代码执行并发上限

并发执行数硬编码为 2，无论本地机器有多少核心。这是按 2c/2G 服务器规格设计的保护措施。多个用户同时触发 Python 执行时，第三个请求会排队等待。

### Help Docs 种子数据

`backend/app/seed/help_docs.json` 里的帮助文档不会在服务启动时自动导入，需要手动通过管理界面或 API 导入。

### MCP 服务器

- `stdio` 类型：需要在运行服务的机器上安装对应的 MCP 服务二进制
- `SSE` / `HTTP` 类型：需要能访问对应的远程 MCP 服务器

---

## 最小可运行配置（核心对话功能）

以下是跑起核心对话功能所需的最少 `.env` 配置（基于 SQLite）：

```env
DATABASE_URL=sqlite+aiosqlite:///./fancy_agent.db
SECRET_KEY=替换成随机字符串
OSS_URL=http://localhost:8000
UPLOAD_DIR=./data/uploads
WORKSPACE_DIR=./data/workspaces
CORS_ORIGINS=http://localhost:5173
```

LLM 的 API Key 在 Fancy Agent 界面里配置，不在 `.env` 中。

可以直接复制 `backend/.env.sqlite.example` 作为起点：

```bash
cp backend/.env.sqlite.example backend/.env
```

---

## 常见问题

### 配置好了 Webhook 但平台发消息没有响应？

首先确认你的服务有公网可访问的地址。最简单的验证方式是用手机 4G 网络（非同一局域网）访问服务的 `/docs` 路由，如果打不开，说明没有公网访问。

### 图片生成报错"API key not found"或"Unauthorized"？

图片工具的 API Key 在 Fancy Agent 的图片工具配置页面中填写，不在 `.env` 中。确认对应提供商的 Key 已经在工具配置里保存。

### Python 代码执行任务排队很久？

并发上限是 2，多人同时用时会排队。这是正常的设计行为，没有配置可以调整。

### 搜索结果质量差？

默认使用 DuckDuckGo，免费但结果精度有限。配置 `SEARCH_PROVIDER=tavily` 和 `TAVILY_API_KEY` 可以切换到质量更好的 Tavily。
