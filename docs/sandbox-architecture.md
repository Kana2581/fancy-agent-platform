# 代码执行沙箱架构（python_exec + workspace 统一）

## 背景

`python_exec` 历史上是**进程内软沙箱**：子进程 + 净化环境 + 白名单 `__import__` + 屏蔽危险内置 + patch 过的 `open`/`io.open`。它抬高了门槛，但对多租户不可信代码原理上可被逃逸（通过被允许的库如 numpy/pandas 的 `__globals__` 链触达 `os`/`ctypes`）。一旦逃逸，进程能看到宿主机文件系统、环境变量、其他租户工作区。

同时 `python_exec` 与 `workspace` 割裂：代码在临时目录跑、产物进 `UPLOAD_DIR/generated/`，而 `ws_*` 操作 `WORKSPACE_DIR/{user}/{session}/`，agent 没法「写代码处理工作区文件」。

本次改造同时解决两件事：**统一**（代码 cwd = 会话工作区）+ **隔离**（执行放进 OS 级隔离的常驻沙箱容器）。

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
| `python_exec.py` | 双路执行（远程 sandbox / 本地子进程）+ 产物登记。 |

## 执行路径

由 `settings.SANDBOX_EXEC_URL` 决定：

- **已配置**（生产/Docker，`http://sandbox:9000`）：`PythonExecTool._arun` POST 到 sandbox，`rel_dir = "{user_id}/{session_id}"`，在 `/workspaces/{rel_dir}` 内执行。
- **未配置**（本地 Windows 开发）：进程内子进程沙箱 `sandbox_runner.execute()`，cwd 同样指向会话工作区，保证「统一」语义一致；远程调用异常时也会自动回退到这条路径。

执行后：新增/改动的工作区文件登记为 `storage_type="workspace"`（进工作区面板）；其中图片（png/jpg/jpeg/gif/webp）另复制到 `UPLOAD_DIR/generated/` 并返回公开 URL，保留聊天内联预览。runner 与 user_code 落在独立临时目录，**不污染工作区**。

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

1. 本地：`cd backend; uv run pytest tests/unit/test_python_exec_persistence.py`（覆盖本地子进程 + 工作区登记 + 图片内联 URL + 读已有文件 + 越界拦截）。
2. Docker：`docker compose up --build` 后 `docker compose ps` 确认 `code_sandbox` healthy；跑挂了 `python_exec`+`workspace_manager` 的 agent，让它 `ws_write` 一个 csv → `python_exec` 用 pandas 读它画图 → 验证能读到、图表内联、产物进工作区面板。
3. 内存：`docker stats` 观察 sandbox 峰值 < 384M、整机 < 2G。
