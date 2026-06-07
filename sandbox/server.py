"""极小代码执行沙箱服务。

常驻容器内运行，backend 通过内网 HTTP 调用本服务执行 Python 代码。
代码在共享挂载的会话工作区 `/workspaces/{rel_dir}` 内执行；产物落在同一个卷上，
backend 直接在宿主侧读取登记，文件不经 HTTP 传输。

隔离边界：
- 容器边界隔离宿主机（强）。
- 租户间隔离靠 sandbox_runner 的软沙箱 open() 限制（执行 cwd 锁到该会话目录）。
- 2c/2G 下用 Semaphore(1) 串行执行，避免并发 OOM。
"""
import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

import sandbox_runner

app = FastAPI(title="code-sandbox", docs_url=None, redoc_url=None)

# 工作区卷在容器内的挂载点（与 backend 共享同一个 docker volume）
WORKSPACES_ROOT = Path(os.environ.get("WORKSPACES_ROOT", "/workspaces")).resolve()
EXEC_TIMEOUT = int(os.environ.get("SANDBOX_EXEC_TIMEOUT", "30"))

# 2c/2G：串行执行，避免两个 numpy/matplotlib 进程同时撑爆内存
_exec_semaphore = asyncio.Semaphore(int(os.environ.get("SANDBOX_CONCURRENCY", "1")))


class ExecRequest(BaseModel):
    code: Optional[str] = Field(default=None, description="要执行的 Python 代码（与 script_path 二选一）")
    rel_dir: str = Field(description="会话工作区相对目录，形如 '{user_id}/{session_id}'")
    timeout: int = Field(default=EXEC_TIMEOUT, description="执行超时（秒）")
    script_path: Optional[str] = Field(
        default=None,
        description="工作区内已有脚本的相对路径（相对 rel_dir），以该文件为入口运行",
    )


def _resolve_workdir(rel_dir: str) -> Path:
    """把 rel_dir 解析到 WORKSPACES_ROOT 下，拒绝绝对路径与越界。"""
    cleaned = (rel_dir or "").strip().lstrip("/").lstrip("\\")
    if not cleaned:
        raise ValueError("rel_dir 不能为空")
    candidate = Path(cleaned)
    if candidate.is_absolute():
        raise ValueError("rel_dir 不允许绝对路径")
    workdir = (WORKSPACES_ROOT / cleaned).resolve()
    if workdir != WORKSPACES_ROOT and WORKSPACES_ROOT not in workdir.parents:
        raise ValueError("rel_dir 越界")
    return workdir


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/exec")
async def exec_code(req: ExecRequest) -> dict:
    try:
        workdir = _resolve_workdir(req.rel_dir)
    except ValueError as e:
        return {"error": str(e), "stdout": "", "stderr": "", "exit_code": -1, "produced": []}

    abs_script = None
    if req.script_path:
        cleaned = req.script_path.strip().lstrip("/").lstrip("\\")
        candidate = (workdir / cleaned).resolve()
        if workdir not in candidate.parents and candidate != workdir:
            return {"error": "script_path 越界", "stdout": "", "stderr": "",
                    "exit_code": -1, "produced": []}
        abs_script = str(candidate)

    timeout = max(1, min(req.timeout, 120))
    async with _exec_semaphore:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: sandbox_runner.execute(
                code=req.code, workdir=str(workdir), timeout=timeout, script_path=abs_script
            ),
        )
