from typing import List, Optional

from langchain_core.tools import BaseTool

from app.core.logging_config import get_logger
from app.utils.langchain.builtin_tools.web_search import build_web_search_tool
from app.utils.langchain.builtin_tools.web_fetch import build_web_fetch_tool
from app.utils.langchain.builtin_tools.python_exec import build_python_exec_tool

logger = get_logger(__name__)

_BUILDERS = {
    "web_search": build_web_search_tool,
    "web_fetch": build_web_fetch_tool,
}


def build_builtin_tools(
    tool_types: List[str],
    user_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    session_id: Optional[str] = None,
    llm_config: Optional[dict] = None,
) -> List[BaseTool]:
    tools = []
    for tool_type in tool_types:
        if tool_type == "scheduled_task_manager":
            if user_id is None:
                logger.warning("Scheduled task manager tool requires user_id, skipping")
                continue
            try:
                from app.utils.langchain.builtin_tools.scheduled_task_tool import build_scheduled_task_tools
                tools.extend(build_scheduled_task_tools(user_id, agent_id=agent_id or 0))
            except Exception:
                logger.exception("Failed to build scheduled_task_manager tools")
            continue

        if tool_type == "skill_manager":
            if user_id is None:
                logger.warning("Skill manager tool requires user_id, skipping")
                continue
            try:
                from app.utils.langchain.builtin_tools.skill_manager_tool import build_skill_manager_tools
                tools.extend(build_skill_manager_tools(user_id, session_id=session_id))
            except Exception:
                logger.exception("Failed to build skill_manager tools")
            continue

        if tool_type == "workspace_manager":
            if user_id is None or not session_id:
                logger.warning("Workspace manager tool requires user_id and session_id, skipping")
                continue
            try:
                from app.utils.langchain.builtin_tools.workspace_tool import build_workspace_tools
                tools.extend(build_workspace_tools(user_id, session_id))
            except Exception:
                logger.exception("Failed to build workspace_manager tools")
            continue

        if tool_type == "memory_manager":
            if user_id is None:
                logger.warning("Memory manager tool requires user_id, skipping")
                continue
            try:
                from app.utils.langchain.builtin_tools.memory_manager_tool import build_memory_manager_tools
                tools.extend(build_memory_manager_tools(user_id))
            except Exception:
                logger.exception("Failed to build memory_manager tools")
            continue

        if tool_type == "prompt_template_manager":
            if user_id is None:
                logger.warning("Prompt template manager tool requires user_id, skipping")
                continue
            try:
                from app.utils.langchain.builtin_tools.prompt_template_tool import build_prompt_template_tools
                tools.extend(build_prompt_template_tools(user_id))
            except Exception:
                logger.exception("Failed to build prompt_template_manager tools")
            continue

        if tool_type == "knowledge_graph_manager":
            if user_id is None:
                logger.warning("Knowledge graph manager tool requires user_id, skipping")
                continue
            try:
                from app.utils.langchain.builtin_tools.knowledge_graph_manager_tool import build_knowledge_graph_tools
                tools.extend(build_knowledge_graph_tools(user_id, llm_config=llm_config))
            except Exception:
                logger.exception("Failed to build knowledge_graph_manager tools")
            continue

        if tool_type == "help_document_manager":
            try:
                from app.utils.langchain.builtin_tools.help_document_tool import build_help_document_tools
                tools.extend(build_help_document_tools())
            except Exception:
                logger.exception("Failed to build help_document_manager tools")
            continue

        if tool_type == "python_exec":
            try:
                tools.append(build_python_exec_tool(user_id=user_id, session_id=session_id))
            except Exception:
                logger.exception("Failed to build python_exec tool")
            continue

        builder = _BUILDERS.get(tool_type)
        if builder is None:
            logger.warning("Unknown builtin tool type: %s, skipping", tool_type)
            continue
        try:
            tools.append(builder())
        except Exception:
            logger.exception("Failed to build builtin tool '%s'", tool_type)
    return tools
