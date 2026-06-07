from sqlalchemy import func, select, Integer, cast, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.session import Session
from app.models.agent import Agent
from app.schemas.stats_schema import (
    TokenSummary,
    AgentTokenStat,
    DailyTokenStat,
)
from app.utils.db_compat import IS_SQLITE


def _input_tokens(col):
    return func.coalesce(
        cast(func.json_extract(col, "$.input_tokens"), Integer), 0
    )


def _output_tokens(col):
    return func.coalesce(
        cast(func.json_extract(col, "$.output_tokens"), Integer), 0
    )


class StatsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self, user_id: int) -> TokenSummary:
        um = ChatMessage.usage_metadata

        stmt = (
            select(
                func.sum(_input_tokens(um)).label("total_input"),
                func.sum(_output_tokens(um)).label("total_output"),
                func.count(ChatMessage.id).label("total_messages"),
                func.count(func.distinct(ChatMessage.session_id)).label("total_sessions"),
            )
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.type == "ai",
            )
        )
        result = await self.db.execute(stmt)
        row = result.one()
        return TokenSummary(
            total_input_tokens=row.total_input or 0,
            total_output_tokens=row.total_output or 0,
            total_messages=row.total_messages or 0,
            total_sessions=row.total_sessions or 0,
        )

    async def get_by_agent(self, user_id: int) -> list[AgentTokenStat]:
        um = ChatMessage.usage_metadata

        stmt = (
            select(
                Agent.id.label("agent_id"),
                Agent.description.label("agent_name"),
                func.sum(_input_tokens(um)).label("input_tokens"),
                func.sum(_output_tokens(um)).label("output_tokens"),
                func.count(ChatMessage.id).label("message_count"),
            )
            .join(Session, ChatMessage.session_id == Session.id)
            .join(Agent, Session.agent_id == Agent.id)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.type == "ai",
            )
            .group_by(Agent.id, Agent.description)
            .order_by(func.sum(_output_tokens(um)).desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            AgentTokenStat(
                agent_id=r.agent_id,
                agent_name=r.agent_name or f"Agent {r.agent_id}",
                input_tokens=r.input_tokens or 0,
                output_tokens=r.output_tokens or 0,
                message_count=r.message_count or 0,
            )
            for r in rows
        ]

    async def get_daily(self, user_id: int, days: int = 30) -> list[DailyTokenStat]:
        um = ChatMessage.usage_metadata

        stmt = (
            select(
                func.date(ChatMessage.created_at).label("date"),
                func.sum(_input_tokens(um)).label("input_tokens"),
                func.sum(_output_tokens(um)).label("output_tokens"),
            )
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.type == "ai",
                ChatMessage.created_at >= (
                    func.datetime("now", f"-{int(days)} days")
                    if IS_SQLITE
                    else func.date_sub(func.now(), text(f"INTERVAL {int(days)} DAY"))
                ),
            )
            .group_by(func.date(ChatMessage.created_at))
            .order_by(func.date(ChatMessage.created_at).asc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            DailyTokenStat(
                date=str(r.date),
                input_tokens=r.input_tokens or 0,
                output_tokens=r.output_tokens or 0,
            )
            for r in rows
        ]
