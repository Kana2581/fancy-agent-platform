from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.agent import Agent
from app.models.agent_api_tool import AgentApiTool
from app.models.agent_builtin_tool import AgentBuiltinTool
from app.models.agent_image_tool import AgentImageTool
from app.models.agent_mcp import AgentMCP
from app.models.api_tool import ApiTool
from app.models.image_tool import ImageTool
from app.models.llm import LLM
from app.models.mcp import MCP
from sqlalchemy import case

class AgentMapper(BaseMapper[Agent]):
    model = Agent

    async def get_full_agent(self, agent_id: int, user_id: int) -> dict | None:
        # 1️⃣ 先查 agent + llm
        agent_stmt = (
            select(Agent, LLM)
            .join(LLM, LLM.id == Agent.model_id)
            .where(
                Agent.id == agent_id,
                Agent.user_id == user_id,
            )
        )

        agent_result = await self.db.execute(agent_stmt)
        row = agent_result.first()

        if not row:
            return None

        agent, llm = row

        # 2️⃣ 查 user 下所有 MCP + 是否属于该 agent
        mcp_stmt = (
            select(
                MCP,
                case(
                    (AgentMCP.agent_id.isnot(None), True),
                    else_=False
                ).label("has_mcp")
            )
            .outerjoin(
                AgentMCP,
                (AgentMCP.mcp_id == MCP.id)
                & (AgentMCP.agent_id == agent_id)
            )
            .where(MCP.user_id == user_id)
        )

        mcp_result = await self.db.execute(mcp_stmt)
        mcp_rows = mcp_result.all()

        mcps = []

        for mcp, has_mcp in mcp_rows:
            mcps.append({
                "id": mcp.id,
                "mcp_name": mcp.mcp_name,
                "transport": mcp.transport,
                "is_builtin": mcp.is_builtin,
                "is_enabled": mcp.is_enabled,
                "created_at": mcp.created_at,
                "updated_at": mcp.updated_at,
                "user_id": mcp.user_id,
                "config_json": mcp.config_json,
                "has_mcp": has_mcp,  # ✅ 关键字段
            })

        # 3️⃣ 查询该 agent 绑定的 API Tools（只返回已绑定的，携带完整配置）
        api_tool_stmt = (
            select(ApiTool)
            .join(AgentApiTool, AgentApiTool.api_tool_id == ApiTool.id)
            .where(AgentApiTool.agent_id == agent_id)
        )
        api_tool_result = await self.db.execute(api_tool_stmt)
        api_tool_rows = api_tool_result.scalars().all()

        api_tools = [
            {
                "id": t.id,
                "user_id": t.user_id,
                "name": t.name,
                "description": t.description,
                "url": t.url,
                "method": t.method,
                "headers": t.headers,
                "param_location": t.param_location,
                "fixed_params": t.fixed_params,
                "tool_params": t.tool_params,
                "response_extract": t.response_extract,
                "response_max_chars": t.response_max_chars,
            }
            for t in api_tool_rows
        ]

        # 4️⃣ 查询该 agent 绑定的图像生成工具
        image_tool_stmt = (
            select(ImageTool)
            .join(AgentImageTool, AgentImageTool.image_tool_id == ImageTool.id)
            .where(AgentImageTool.agent_id == agent_id)
        )
        image_tool_result = await self.db.execute(image_tool_stmt)
        image_tool_rows = image_tool_result.scalars().all()

        image_tools = [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "provider": t.provider,
                "api_key": t.api_key,
                "base_url": t.base_url,
                "model": t.model,
                "default_size": t.default_size,
                "default_quality": t.default_quality,
                "default_style": t.default_style,
                "extra_params": t.extra_params,
                "support_img2img": t.support_img2img,
            }
            for t in image_tool_rows
        ]

        # 5️⃣ 查询该 agent 绑定的内置工具
        builtin_stmt = select(AgentBuiltinTool.tool_type).where(
            AgentBuiltinTool.agent_id == agent_id
        )
        builtin_result = await self.db.execute(builtin_stmt)
        builtin_types = [row[0] for row in builtin_result.all()]

        return {
            "id": agent.id,
            "user_id": agent.user_id,
            "avatar": agent.avatar,
            "description": agent.description,
            "system_prompt": agent.system_prompt,
            "max_token_size": agent.max_token_size,
            "model_id": agent.model_id,
            "human_in_the_loop": agent.human_in_the_loop,
            "llm": {
                "id": llm.id,
                "provider": llm.provider,
                "model_name": llm.model_name,
                "base_url": llm.base_url,
                "api_key": llm.api_key,
                "created_at": llm.created_at,
                "updated_at": llm.updated_at,
                "user_id": llm.user_id,
            },
            "mcps": mcps,
            "api_tools": api_tools,
            "image_tools": image_tools,
            "builtin_tools": builtin_types,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
        }
