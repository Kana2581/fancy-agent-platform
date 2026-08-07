"""Bash execution tool backed exclusively by the remote isolated sandbox."""
import json
from pathlib import Path
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.skill_catalog_service import skill_root_mounts
from app.utils.sandbox_client import SandboxUnavailableError, sandbox_client
from app.utils.langchain.builtin_tools.sandbox_products import handle_sandbox_products

logger = get_logger(__name__)


class BashExecInput(BaseModel):
    command: str = Field(description="要在当前会话工作区或已挂载 Skill 目录内运行的 Bash 命令")
    cwd: Optional[str] = Field(default=None, description="内部兼容参数；模型侧 sandbox 固定从 /workspace 执行")


class BashExecTool(BaseTool):
    name: str = "bash_exec"
    description: str = (
        "在隔离 sandbox 中运行 Bash 命令，默认从 /workspace 执行。"
        "只允许写入 /workspace 和 /skills/user；/skills/system 只读。"
        "禁止 ..、其他绝对路径和网络访问；工作区文件变更会自动登记。"
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
                cwd=cwd, timeout=30, skill_roots=skill_root_mounts(self.user_id),
            )
        except SandboxUnavailableError as exc:
            logger.exception(
                "sandbox request failed user_id=%s session_id=%s cwd=%r",
                self.user_id, self.session_id, cwd,
            )
            return json.dumps({"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1, "files": []}, ensure_ascii=False)
        try:
            workdir = Path(settings.WORKSPACE_DIR) / str(self.user_id) / self.session_id
            products = payload.pop("changed_files", payload.pop("produced", []))
            payload["files"] = await handle_sandbox_products(
                self.user_id,
                self.session_id,
                workdir,
                products,
            )
            deleted = payload.pop("deleted_files", [])
            if deleted:
                from app.utils.langchain.builtin_tools.workspace_tool import _unregister_workspace_file
                for path in deleted:
                    await _unregister_workspace_file(self.user_id, self.session_id, path)
        except Exception as exc:
            logger.exception(
                "sandbox response handling failed user_id=%s session_id=%s cwd=%r",
                self.user_id, self.session_id, cwd,
            )
            return json.dumps({
                "error": f"sandbox 结果处理失败: {exc}",
                "error_type": type(exc).__name__,
                "stdout": payload.get("stdout", ""),
                "stderr": payload.get("stderr", ""),
                "exit_code": payload.get("exit_code", -1),
                "files": [],
            }, ensure_ascii=False)
        return json.dumps(payload, ensure_ascii=False)

    def _run(self, **kwargs) -> str:
        raise NotImplementedError("Use async version")


def build_bash_exec_tool(user_id: Optional[int] = None, session_id: Optional[str] = None) -> BaseTool:
    return BashExecTool(user_id=user_id, session_id=session_id)
