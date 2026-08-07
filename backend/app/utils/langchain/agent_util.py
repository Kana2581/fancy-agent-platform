from typing import Any, List, Tuple

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from app.schemas.dto.langchian import ValidAgent, ValidChatModel
from app.services.skill_catalog_service import SkillCatalogEntry, scan_skill_catalog
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Optional
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain.agents.middleware.model_call_limit import ModelCallLimitMiddleware

import asyncio
import json
from datetime import datetime, timezone, timedelta

from app.core.logging_config import get_logger
from app.utils.langchain.http_tool_factory import build_tool_from_config
from app.utils.langchain.image_tool_factory import build_image_tool_from_config
from app.utils.langchain.middleware import (
    MessageLimitMiddleware,
    ToolCallInterruptMiddleware,
    ToolExecutionLoggingMiddleware,
)

logger = get_logger(__name__)

def create_langchain_agent_with_middleware(model: BaseChatModel,
                                           tools: Optional[List[BaseTool]],
                                           system_prompt: str = "You are a helpful assistant.",
                                           max_token=8000,
                                           human_in_the_loop=False,
                                           response_format: Any = None):
    today = datetime.now(tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    system_prompt = f"{system_prompt}\n\n今天日期：{today}"

    from app.core.config import settings
    tool_limiter = ToolCallLimitMiddleware(run_limit=settings.AGENT_TOOL_CALL_LIMIT, exit_behavior="end")
    model_limiter = ModelCallLimitMiddleware(run_limit=settings.AGENT_MODEL_CALL_LIMIT, exit_behavior="end")
    tool_logger = ToolExecutionLoggingMiddleware()
    message_limiter = MessageLimitMiddleware(max_token)
    middleware = [tool_logger, tool_limiter, model_limiter, message_limiter]
    if human_in_the_loop:
        middleware = [ToolCallInterruptMiddleware(True)] + middleware

    return create_agent(
        model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
        response_format=response_format,
    )


async def _build_model_and_tools(
    agent_data: ValidAgent,
    session_id: Optional[str] = None,
    skills: Optional[List[SkillCatalogEntry]] = None,
) -> Tuple[BaseChatModel, List[BaseTool]]:
    """Shared logic for building the LLM model and tool list from agent config."""
    model_config = ValidChatModel.model_validate(agent_data.llm)
    model_kwargs = model_config.model_dump()
    if model_config.model_provider in ("openai", "openai-like"):
        model_kwargs["stream_usage"] = True
    model = init_chat_model(**model_kwargs)

    tools: List[BaseTool] = []

    if skills is None:
        skills = await _get_effective_skills(agent_data)

    if agent_data.mcps:
        client_config = {}
        for mcp in agent_data.mcps:
            config = mcp.config_json or {}
            if isinstance(config, str):
                config = json.loads(config)
            client_config[mcp.mcp_name] = {
                "transport": mcp.transport,
                **config,
            }

        client = MultiServerMCPClient(client_config)
        try:
            tools.extend(await asyncio.wait_for(client.get_tools(), timeout=30))
        except asyncio.TimeoutError:
            logger.warning("MCP tool fetch timed out (>30s) for servers: %s", list(client_config.keys()))
        except Exception:
            logger.exception("Failed to fetch tools from MCPs")

    if agent_data.api_tools:
        for api_tool in agent_data.api_tools:
            try:
                http_tool = build_tool_from_config(api_tool.model_dump())
                tools.append(http_tool)
            except Exception:
                logger.exception("Failed to build HTTP tool '%s'", api_tool.name)

    if agent_data.image_tools:
        for image_tool in agent_data.image_tools:
            try:
                img_lc_tool = build_image_tool_from_config(image_tool.model_dump(), user_id=agent_data.user_id)
                tools.append(img_lc_tool)
            except Exception:
                logger.exception("Failed to build image tool '%s'", image_tool.name)

    if agent_data.builtin_tools:
        from app.utils.langchain.builtin_tools.factory import build_builtin_tools
        llm_config_dict = agent_data.llm.model_dump() if agent_data.llm else None
        tools.extend(build_builtin_tools(
            agent_data.builtin_tools,
            user_id=agent_data.user_id,
            agent_id=agent_data.id,
            session_id=session_id,
            llm_config=llm_config_dict,
        ))

    return model, tools


async def _get_core_memory_prompt(user_id: int) -> str:
    """Load core memories for user and return a formatted prompt snippet."""
    try:
        from app.deps.db import get_db_session
        from app.mappers.user_memory_mapper import UserMemoryMapper
        async with get_db_session() as db:
            memories = await UserMemoryMapper(db).list_by_user(user_id, memory_type="core")
        if not memories:
            return ""
        lines = "\n".join(f"- {m.key}: {m.content}" for m in memories)
        return f"\n\n### 我的记忆（核心）\n{lines}"
    except Exception:
        logger.exception("Failed to load core memories")
        return ""


async def _get_effective_skills(agent_data: ValidAgent) -> List[SkillCatalogEntry]:
    """Scan all current system and user Skill packages for this user."""
    try:
        return await asyncio.to_thread(scan_skill_catalog, agent_data.user_id, "all", False)
    except Exception:
        logger.exception("Failed to scan filesystem Skills")
        return []


async def _build_system_prompt(
    agent_data: ValidAgent,
    skills: Optional[List[SkillCatalogEntry]] = None,
    tools: Optional[List[BaseTool]] = None,
) -> str:
    """Return system prompt; core memories always included so the model has them regardless of tools."""
    system_prompt = agent_data.system_prompt or ""
    if agent_data.user_id:
        system_prompt += await _get_core_memory_prompt(agent_data.user_id)
    if agent_data.image_tools:
        system_prompt += (
            "\n\nWhen you generate an image using an image tool, "
            "you MUST display it in your response using markdown image syntax: "
            "![description](url)"
        )
    if skills is None:
        skills = await _get_effective_skills(agent_data)
    skill_runtime_available = any(
        getattr(tool, "name", None) == "sandbox"
        and getattr(tool, "supports_skills", False)
        for tool in (tools or [])
    )
    if skills and skill_runtime_available:
        entries = "\n".join(
            f"- {skill.name} [{skill.scope}] ({skill.mount_path}): {skill.description}"
            for skill in skills
        )
        system_prompt += (
            "\n\n## 可用 Skills\n" + entries
            + "\n对匹配的任务，必须先用 sandbox(command=...) 读取对应目录下的 SKILL.md，再按其中说明执行。"
            + "必须直接使用清单给出的 mount_path；不要根据 Skill 名称推断 system/user 目录。系统 Skill 只读；用户 Skill 可在 /skills/user 下创建、修改和执行。"
        )
    return system_prompt


async def get_langchian_agent(
    agent_data: ValidAgent,
    session_id: Optional[str] = None,
    response_format: Any = None,
):
    """Build a compiled LangGraph agent from ValidAgent config."""
    if agent_data.llm is None:
        raise ValueError("Agent has no LLM config")

    skills = await _get_effective_skills(agent_data)
    model, tools = await _build_model_and_tools(agent_data, session_id=session_id, skills=skills)
    system_prompt = await _build_system_prompt(agent_data, skills=skills, tools=tools)
    return create_langchain_agent_with_middleware(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        max_token=agent_data.max_token_size,
        human_in_the_loop=agent_data.human_in_the_loop,
        response_format=response_format,
    )


async def get_langchain_agent_and_tools(
    agent_data: ValidAgent,
    session_id: Optional[str] = None,
    response_format: Any = None,
) -> Tuple:
    """Build agent and return (agent, tools_list) for use in the approve-tool endpoint."""
    if agent_data.llm is None:
        raise ValueError("Agent has no LLM config")

    skills = await _get_effective_skills(agent_data)
    model, tools = await _build_model_and_tools(agent_data, session_id=session_id, skills=skills)
    system_prompt = await _build_system_prompt(agent_data, skills=skills, tools=tools)
    agent = create_langchain_agent_with_middleware(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        max_token=agent_data.max_token_size,
        human_in_the_loop=agent_data.human_in_the_loop,
        response_format=response_format,
    )
    return agent, tools
