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
from pathlib import Path
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging_config import get_logger
from app.utils import sandbox_runner
from app.utils.sandbox_client import SandboxUnavailableError, sandbox_client
from app.utils.langchain.builtin_tools.sandbox_products import handle_sandbox_products
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
class PythonExecInput(BaseModel):
    code: Optional[str] = Field(default=None, description="要执行的 Python 代码（与 script 二选一）")
    script: Optional[str] = Field(
        default=None,
        description="运行工作区内已有脚本文件的相对路径。Skill package 中的脚本请使用 bash_exec。与 code 二选一。",
    )


class PythonExecTool(BaseTool):
    name: str = "python_exec"
    description: str = (
        "在隔离 sandbox 的当前会话工作区内执行 Python 代码并返回输出。代码的 cwd 就是工作区，"
        "可直接读写工作区文件（与 ws_read/ws_write 共享同一目录）。"
        "用 code 传内联代码，或用 script 运行工作区里已有的脚本文件。Skill package 中的脚本请使用 bash_exec。"
        "支持 matplotlib：调用 plt.show() 时图表自动保存并以图片返回。"
        "新生成的文件会出现在用户的「工作区文件」面板。执行超时 30 秒，不提供网络访问。"
    )
    args_schema: Type[BaseModel] = PythonExecInput
    user_id: Optional[int] = None
    session_id: Optional[str] = None

    # ---------- 执行 ----------

    async def _exec_remote(
        self, code: Optional[str], rel_dir: str, script_path: Optional[str] = None
    ) -> dict:
        """Run through the remote runtime. Production never falls back locally."""
        return await sandbox_client().execute(
            runtime="python", rel_dir=rel_dir, code=code,
            timeout=_EXEC_TIMEOUT, script_path=script_path,
        )

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

    async def _handle_products(self, workdir: Path, produced: List[object]) -> List[dict]:
        """Compatibility wrapper for legacy Python execution tests."""
        return await handle_sandbox_products(
            self.user_id,
            self.session_id,
            workdir,
            produced,
        )

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

            # The remote runtime creates the session directory. Local development
            # retains the subprocess fallback and must create it here.
            workdir = Path(settings.WORKSPACE_DIR) / str(self.user_id) / self.session_id
            if not settings.SANDBOX_EXEC_URL:
                workdir = ensure_workspace(self.user_id, self.session_id)
            rel_dir = f"{self.user_id}/{self.session_id}"

            # script 模式：本地回退需要绝对路径；远程 sandbox 自己验证相对路径。
            rel_script = None
            abs_script = None
            if script:
                if settings.SANDBOX_EXEC_URL:
                    rel_script = script
                else:
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
                except SandboxUnavailableError as exc:
                    return json.dumps({"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1, "files": []}, ensure_ascii=False)
            else:
                payload = await self._exec_local(code, str(workdir), script_path=abs_script)

            produced = payload.pop("changed_files", payload.pop("produced", []))
            payload["files"] = await self._handle_products(workdir, produced)
            deleted = payload.pop("deleted_files", [])
            if deleted:
                from app.utils.langchain.builtin_tools.workspace_tool import _unregister_workspace_file
                for path in deleted:
                    await _unregister_workspace_file(self.user_id, self.session_id, path)
            return json.dumps(payload, ensure_ascii=False)


def build_python_exec_tool(
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> BaseTool:
    return PythonExecTool(user_id=user_id, session_id=session_id)
