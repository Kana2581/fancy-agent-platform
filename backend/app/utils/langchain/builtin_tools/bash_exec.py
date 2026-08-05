"""Bash execution tool backed exclusively by the remote isolated sandbox."""
import json
from pathlib import Path
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import settings
from app.utils.sandbox_client import SandboxUnavailableError, sandbox_client


class BashExecInput(BaseModel):
    command: str = Field(description="要在当前会话工作区内运行的 Bash 命令")
    cwd: Optional[str] = Field(default=None, description="可选的工作区相对目录")


class BashExecTool(BaseTool):
    name: str = "bash_exec"
    description: str = (
        "在隔离 sandbox 的当前会话工作区运行 Bash 命令。仅能访问当前会话工作区，"
        "没有网络访问；新增或修改的文件会出现在用户的工作区文件面板。"
    )
    args_schema: Type[BaseModel] = BashExecInput
    user_id: Optional[int] = None
    session_id: Optional[str] = None

    async def _arun(self, command: str, cwd: Optional[str] = None) -> str:
        if not self.user_id or not self.session_id:
            return json.dumps({"error": "当前上下文无会话，无法执行 Bash"}, ensure_ascii=False)
        try:
            payload = await sandbox_client().execute(
                runtime="bash", rel_dir=f"{self.user_id}/{self.session_id}", command=command,
                cwd=cwd, timeout=30,
            )
        except SandboxUnavailableError as exc:
            return json.dumps({"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1, "files": []}, ensure_ascii=False)

        from app.utils.langchain.builtin_tools.python_exec import PythonExecTool

        workdir = Path(settings.WORKSPACE_DIR) / str(self.user_id) / self.session_id
        products = payload.pop("changed_files", payload.pop("produced", []))
        payload["files"] = await PythonExecTool(
            user_id=self.user_id, session_id=self.session_id
        )._handle_products(workdir, products)
        deleted = payload.pop("deleted_files", [])
        if deleted:
            from app.utils.langchain.builtin_tools.workspace_tool import _unregister_workspace_file
            for path in deleted:
                await _unregister_workspace_file(self.user_id, self.session_id, path)
        return json.dumps(payload, ensure_ascii=False)

    def _run(self, **kwargs) -> str:
        raise NotImplementedError("Use async version")


def build_bash_exec_tool(user_id: Optional[int] = None, session_id: Optional[str] = None) -> BaseTool:
    return BashExecTool(user_id=user_id, session_id=session_id)
