# Bash 工作区沙箱架构

## 背景

历史上 Python、Bash 和 workspace 文件操作分别暴露给模型，工具参数重复且容易误选。

现在模型只看到一个 `sandbox(command)` Bash 工具，默认 cwd 是会话工作区；文件读写和脚本执行都通过 Bash 完成。执行仍放进 OS 级隔离的常驻沙箱容器。

## 拓扑

```
┌──────────┐  HTTP POST /exec           ┌──────────────────────┐
│ backend  │ ─────────────────────────► │ sandbox 容器          │
│ (FastAPI)│  {code, rel_dir, timeout}  │  server.py (FastAPI)  │
│          │ ◄───────────────────────── │  sandbox_runner.py    │
└────┬─────┘  {stdout,stderr,produced}  └──────────┬───────────┘
     │                                             │
     │   共享同一个 docker volume `workspaces`        │
     └────────► /data/workspaces   /workspaces ◄────┘
                  (backend 侧)      (sandbox 侧)
```

- **不挂 `docker.sock`**：backend 只发内网 HTTP，沙箱由 compose 常驻，backend 无需 Docker 控制权（挂 socket = 宿主机 root，是安全降级，刻意回避）。
- **文件不经 HTTP**：sandbox 在共享卷上落盘，backend 直接在宿主侧读取并登记 `ChatFile`。
- 评估过 LangChain DeepAgents backends，结论是不采用——其 Sandbox 后端只有 Modal/Daytona（云 SaaS，离开本机+收费）、Deno（非 Python）、local VFS（无 OS 隔离），都解决不了「自托管 Python + OS 隔离」，反而要再写自定义 backend + 迁移整套运行时。

## 组件

| 文件 | 作用 |
|------|------|
| `backend/app/utils/sandbox_runner.py` | **单一事实来源**。纯 stdlib、无 app 依赖的软沙箱 runner（runner 模板 + 净化环境 + 白名单 import + open 限制 + 执行前后文件 diff）。backend 本地回退与 sandbox 容器**共用同一份**，构建时 COPY 进镜像。 |
| `sandbox/server.py` | 极小 FastAPI：`POST /exec`、`GET /health`。`Semaphore(1)` 串行执行。 |
| `sandbox/Dockerfile` | `python:3.12-slim` + 预装固定数据/计算环境 + 沙箱服务。build context 是**仓库根**，以便 COPY backend 下的 runner。 |
| `sandbox_tool.py` | 对模型暴露单参数 `sandbox(command)` 工具。 |

Skill 目录由 sandbox 在执行 Bash 时按用户上下文挂载：系统目录映射为
`/skills/system` 且只读，当前用户目录映射为 `/skills/user` 且可写。Skill
包不再通过数据库绑定或专用模型工具暴露；后端在 Agent 构建和 Bash 执行
完成后现场扫描文件系统。

模型侧 Bash 的 cwd 固定为 `/workspace`；访问 Skill 时在命令中使用清单给出的
`/skills/system/...` 或 `/skills/user/...` 路径。其他绝对路径和 `..` 均拒绝。

模型侧使用 `sandbox(command)` 处理工作区、Bash 和文件系统 Skill；需要 Python
时也在 Bash 命令中调用。上传附件在聊天消息构建阶段自动注入，不再作为 sandbox operation 暴露。

## 执行路径

由 `settings.SANDBOX_EXEC_URL` 决定：

- **已配置**（生产/Docker，`http://sandbox:9000`）：`sandbox(command)` 通过内部 Bash 执行器 POST 到 sandbox，`rel_dir = "{user_id}/{session_id}"`，在 `/workspaces/{rel_dir}` 内执行。
- **未配置**（本地 Windows 开发）：Bash 工具明确返回 sandbox 未配置错误。

执行后：新增/改动的工作区文件登记为 `storage_type="workspace"`（进工作区面板）；其中图片（png/jpg/jpeg/gif/webp）另复制到 `UPLOAD_DIR/generated/` 并返回公开 URL，保留聊天内联预览。runner 与 user_code 落在独立临时目录，**不污染工作区**。

用户 Skill 根目录也在 sandbox 执行期间使用暂存副本。工作区和用户 Skill
的新增/修改内容共同参与单文件、Session 和用户总量配额校验，只有校验通过
才提交到共享卷；配额失败不会留下 Skill 文件。

## 安全模型与权衡

- **宿主机隔离（强）**：容器边界。即使软沙箱被逃逸，攻击者也被关在沙箱容器内，读不到宿主机文件/凭证。
- **租户间隔离（中）**：共享常驻容器内，靠保留的软沙箱 `open()` 限制——每次执行的 cwd 锁到该会话目录，`open`/`io.open` 拒绝访问工作区外路径。若未来需要硬隔离，可在 sandbox 内为每次执行加 nsjail/bwrap 命名空间。
- **容器内 root**：共享 `workspaces` 卷由 backend(root) 创建，沙箱需写入产物，切非 root 会因卷 UID 不一致写不了。容器内 root 仅在叠加内核逃逸时才危险（超出本项目威胁模型）。
- **可选硬化**（按需加到 compose 的 sandbox 服务）：`read_only: true` 根文件系统 + `tmpfs: /tmp` + `cap_drop: [ALL]` + 限制网络。

## 内存预算（2c/2G 关键约束）

| 服务 | 内存上限 |
|------|----------|
| db (mysql) | 512M |
| backend | 512M（从 600M 下调，给 sandbox 让位） |
| sandbox | 384M |
| nginx | 不限（很小） |

- sandbox 基线（uvicorn + fastapi）很小；峰值出现在用户代码 `import pandas/matplotlib` 时（约 150–250M）。`Semaphore(1)` 串行执行避免并发叠加。
- 预装集合（`sandbox/requirements.txt`）：numpy/pandas/matplotlib/scipy/scikit-learn/seaborn/pillow。**刻意不装** opencv/skimage/plotly/bokeh（太重，会撑爆 384M）。`sandbox_runner.ALLOWED_MODULES` 仍列出它们——白名单是「允许」，镜像是「可用」；导入未安装的会得到清晰 ImportError。
- 若内存吃紧：精简 `sandbox/requirements.txt`（如去掉 scipy/sklearn）、或调高 sandbox `memory` 上限、或升服务器配置。

## 运维

- 改了 runner 逻辑后，sandbox 镜像需重建：`docker compose build sandbox`。
- 沙箱不对外暴露端口（仅 `expose: 9000` 走 compose 内网）。
- backend 未改动新增依赖（httpx 已有），无需重跑 `uv export`。

## 验证要点

1. 本地：`cd backend; uv run pytest tests/unit/test_bash_exec.py tests/unit/test_agent_skill_defaults.py`。
2. Docker：`docker compose up --build` 后 `docker compose ps` 确认 `code_sandbox` healthy；让 agent 通过 `sandbox(command)` 写入一个 csv，再用 Bash/Python 命令读取并生成图表，验证文件登记和图片内联。
3. 内存：`docker stats` 观察 sandbox 峰值 < 384M、整机 < 2G。
