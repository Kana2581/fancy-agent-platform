"""Single-purpose Bash sandbox exposed to the model."""

import json
import traceback
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.logging_config import get_logger
from app.utils.langchain.builtin_tools.bash_exec import BashExecTool

logger = get_logger(__name__)


class SandboxInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(
        description=(
            "要执行的 Bash 命令。默认工作目录是当前会话的 /workspace。"
            "工作区文件的列出、读取、创建、修改和删除都直接用 Bash 命令完成；"
            "需要 Python 时也通过 Bash 调用 python。"
        )
    )


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


class SandboxTool(BaseTool):
    name: str = "sandbox"
    description: str = (
        "在隔离环境中执行 Bash 命令，唯一参数是 command，默认工作目录固定为当前会话的 /workspace。"
        "仅在需要操作文件、运行命令或执行脚本时调用；普通问答或只需在回复中展示文字时不要调用。"
        "工作区文件的列出、读取、创建、修改和删除都使用 Bash；需要 Python 时在 command 中调用 python。"
        "只允许写入 /workspace 及 /skills/user；/skills/system 只允许读取；"
        "禁止访问其他绝对路径、使用 .. 越界或访问网络。"
        "工作区内新增、修改和删除的文件会自动同步到工作区文件面板。"
    )
    args_schema: Type[BaseModel] = SandboxInput
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    bash_tool: Optional[BashExecTool] = Field(default=None, exclude=True)
    supports_skills: bool = False

    async def _arun(self, command: str) -> str:
        if not command or not command.strip():
            return _error("sandbox 必须提供非空 command")
        if self.bash_tool is None:
            return _error("当前上下文没有可用的 Bash 执行能力")
        try:
            return await self.bash_tool._arun(command=command)
        except Exception as exc:
            logger.exception(
                "sandbox Bash execution failed user_id=%s session_id=%s command=%r",
                self.user_id,
                self.session_id,
                command,
            )
            return json.dumps({
                "error": "sandbox Bash 执行异常",
                "error_type": type(exc).__name__,
                "exception": str(exc),
                "traceback": traceback.format_exc(limit=8),
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "files": [],
            }, ensure_ascii=False)

    def _run(self, **kwargs) -> str:
        raise NotImplementedError("Use async version")


def build_sandbox_tool(
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> BaseTool:
    bash_tool = None
    if user_id is not None and session_id:
        bash_tool = BashExecTool(user_id=user_id, session_id=session_id)

    return SandboxTool(
        user_id=user_id,
        session_id=session_id,
        bash_tool=bash_tool,
        supports_skills=bool(bash_tool and settings.SANDBOX_EXEC_URL),
    )
