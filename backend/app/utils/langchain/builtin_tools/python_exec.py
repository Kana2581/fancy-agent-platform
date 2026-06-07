"""python_exec 内置工具 —— 在会话工作区里执行 Python 代码（代码与文件统一）。

两条执行路径，由 settings.SANDBOX_EXEC_URL 决定：
- **已配置**（生产/Docker）：POST 到常驻 sandbox 容器，在共享挂载的会话工作区内执行。
  代码可读写工作区文件、matplotlib 产物落在工作区。容器边界隔离宿主机。
- **未配置**（本地 Windows 开发）：进程内子进程沙箱（app.utils.sandbox_runner），
  同样以会话工作区为 cwd，保证「统一」语义一致。

产物登记：执行后新增/改动的工作区文件登记为 storage_type="workspace"（出现在工作区面板）；
其中图片另复制到 UPLOAD_DIR/generated/ 并返回公开 URL，保留聊天内联预览。
"""
import asyncio
import json
import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import List, Optional, Type

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging_config import get_logger
from app.utils import sandbox_runner
from app.utils.workspace_path import (
    PathTraversalError,
    ensure_workspace,
    relative_to_root,
    safe_resolve,
)

logger = get_logger(__name__)

# 最多允许 2 个 python_exec 并发（backend 侧），防止 2c2g 服务器 OOM
_exec_semaphore = asyncio.Semaphore(2)

_EXEC_TIMEOUT = 30
# 可内联预览的图片扩展名（生成后发布到 generated/ 走公开 URL）
_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp"}


class PythonExecInput(BaseModel):
    code: Optional[str] = Field(default=None, description="要执行的 Python 代码（与 script 二选一）")
    script: Optional[str] = Field(
        default=None,
        description="运行工作区内已有脚本文件的相对路径（如 use_skill 物化出来的 .skills/<name>/x.py）。与 code 二选一。",
    )


class PythonExecTool(BaseTool):
    name: str = "python_exec"
    description: str = (
        "在当前会话工作区内执行 Python 代码并返回输出。代码的 cwd 就是工作区，"
        "可直接读写工作区文件（与 ws_read/ws_write 共享同一目录）。"
        "用 code 传内联代码，或用 script 运行工作区里已有的脚本文件（如 use_skill 物化的技能脚本）。"
        "支持 matplotlib：调用 plt.show() 时图表自动保存并以图片返回。"
        "新生成的文件会出现在用户的「工作区文件」面板。执行超时 30 秒。"
    )
    args_schema: Type[BaseModel] = PythonExecInput
    user_id: Optional[int] = None
    session_id: Optional[str] = None

    # ---------- 执行 ----------

    async def _exec_remote(
        self, code: Optional[str], rel_dir: str, script_path: Optional[str] = None
    ) -> dict:
        """POST 到常驻 sandbox 容器执行。失败时抛出，由调用方决定是否回退。"""
        url = settings.SANDBOX_EXEC_URL.rstrip("/") + "/exec"
        async with httpx.AsyncClient(timeout=_EXEC_TIMEOUT + 15) as client:
            resp = await client.post(
                url,
                json={
                    "code": code,
                    "rel_dir": rel_dir,
                    "timeout": _EXEC_TIMEOUT,
                    "script_path": script_path,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def _exec_local(
        self, code: Optional[str], workdir: str, script_path: Optional[str] = None
    ) -> dict:
        """进程内子进程沙箱执行（本地开发回退）。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: sandbox_runner.execute(
                code=code, workdir=workdir, timeout=_EXEC_TIMEOUT, script_path=script_path
            ),
        )

    # ---------- 产物登记 ----------

    def _publish_image_to_generated(self, src: Path) -> Optional[str]:
        """把图片产物复制到 UPLOAD_DIR/generated/<date>/，返回公开 URL（供聊天内联）。"""
        try:
            upload_dir = getattr(settings, "UPLOAD_DIR", "/data/uploads")
            oss_url = settings.OSS_URL.rstrip("/")
            date_str = date.today().strftime("%Y/%m/%d")
            save_dir = Path(upload_dir) / "generated" / date_str
            save_dir.mkdir(parents=True, exist_ok=True)
            ext = src.suffix.lstrip(".") or "png"
            filename = f"{uuid.uuid4().hex}.{ext}"
            shutil.copy2(src, save_dir / filename)
            return f"{oss_url}/generated/{date_str}/{filename}"
        except Exception:
            logger.exception("python_exec publish image to generated failed")
            return None

    async def _handle_products(self, workdir: Path, produced: List[str]) -> List[dict]:
        """把执行新增/改动的工作区文件登记为 workspace 文件；图片另发布到 generated/ 取内联 URL。"""
        # 延迟导入，避免与 workspace_tool 形成循环依赖
        from app.utils.langchain.builtin_tools.workspace_tool import _register_workspace_file

        files: List[dict] = []
        for rel in produced:
            target = (workdir / rel)
            if not target.exists() or not target.is_file():
                continue
            entry: dict = {"path": relative_to_root(self.user_id, self.session_id, target)}
            try:
                entry["size"] = target.stat().st_size
            except OSError:
                pass
            file_id = await _register_workspace_file(self.user_id, self.session_id, target)
            if file_id is not None:
                entry["file_id"] = file_id
            if target.suffix.lower().lstrip(".") in _IMAGE_EXTS:
                url = self._publish_image_to_generated(target)
                if url:
                    entry["url"] = url
            files.append(entry)
        return files

    # ---------- LangChain 入口 ----------

    def _run(self, code: str) -> str:
        # 同步路径：无会话上下文，落临时目录、不持久化（子线程/单测兜底）。
        import tempfile
        tmp = tempfile.mkdtemp(prefix="sandbox_scratch_")
        try:
            payload = sandbox_runner.execute(code, tmp, _EXEC_TIMEOUT)
            payload["files"] = [{"filename": Path(p).name} for p in payload.pop("produced", [])]
            return json.dumps(payload, ensure_ascii=False)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    async def _arun(self, code: Optional[str] = None, script: Optional[str] = None) -> str:
        if not code and not script:
            return json.dumps({"error": "需要提供 code 或 script 之一"}, ensure_ascii=False)

        async with _exec_semaphore:
            # 无会话上下文：退化为无持久化的临时目录执行（script 需要工作区，不支持）
            if not self.user_id or not self.session_id:
                if script:
                    return json.dumps({"error": "当前上下文无会话，无法用 script 运行工作区脚本"}, ensure_ascii=False)
                return await asyncio.get_event_loop().run_in_executor(None, self._run, code)

            workdir = ensure_workspace(self.user_id, self.session_id)
            rel_dir = f"{self.user_id}/{self.session_id}"

            # script 模式：校验路径在工作区内
            rel_script = None
            abs_script = None
            if script:
                try:
                    target = safe_resolve(self.user_id, self.session_id, script)
                except PathTraversalError as e:
                    return json.dumps({"error": str(e)}, ensure_ascii=False)
                if not target.exists() or not target.is_file():
                    return json.dumps({"error": f"脚本不存在: {script}"}, ensure_ascii=False)
                abs_script = str(target)
                rel_script = relative_to_root(self.user_id, self.session_id, target)

            if settings.SANDBOX_EXEC_URL:
                try:
                    payload = await self._exec_remote(code, rel_dir, script_path=rel_script)
                except Exception:
                    logger.exception("sandbox 远程执行失败，回退本地子进程沙箱")
                    payload = await self._exec_local(code, str(workdir), script_path=abs_script)
            else:
                payload = await self._exec_local(code, str(workdir), script_path=abs_script)

            produced = payload.pop("produced", [])
            payload["files"] = await self._handle_products(workdir, produced)
            return json.dumps(payload, ensure_ascii=False)


def build_python_exec_tool(
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> BaseTool:
    return PythonExecTool(user_id=user_id, session_id=session_id)
