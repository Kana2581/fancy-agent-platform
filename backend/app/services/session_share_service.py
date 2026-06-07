import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db_session
from app.mappers.agent_mapper import AgentMapper
from app.mappers.chat_message_mapper import ChatMessageMapper
from app.mappers.session_mapper import SessionMapper
from app.mappers.session_share_mapper import SessionShareMapper
from app.models.session_share import SessionShare
from app.schemas.session_share_schema import SessionShareCreate, SharedMessage, SharedSessionView

_SLUG_ALPHABET = string.ascii_lowercase + string.digits

_TOOL_PLACEHOLDER = "[工具输出在分享页中已隐藏]"
_TEXT_TRUNCATE = 5000


def _generate_slug(length: int = 16) -> str:
    return "".join(secrets.choice(_SLUG_ALPHABET) for _ in range(length))


def _sanitize_message_content(msg) -> object:
    """脱敏消息内容：tool 类型隐藏；其它仅截断超长文本，避免一次性返回超大 payload。"""
    msg_type = (msg.type or "").lower()
    if msg_type == "tool":
        return _TOOL_PLACEHOLDER
    content = msg.content
    if isinstance(content, str):
        if len(content) > _TEXT_TRUNCATE:
            return content[:_TEXT_TRUNCATE] + "..."
        return content
    return content  # list / dict 直接透传


class SessionShareService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = SessionShareMapper(db)

    async def create(
        self,
        session_id: str,
        user_id: int,
        data: SessionShareCreate,
    ) -> SessionShare:
        # 校验 session 归属
        session = await SessionMapper(self.db).get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise ValueError("Session not found")

        for _ in range(5):
            slug = _generate_slug()
            existing = await self.mapper.get_by_slug(slug)
            if existing is None:
                break
        else:
            raise RuntimeError("无法生成唯一的 share slug")

        expires_at: Optional[datetime] = None
        if data.expires_in_hours and data.expires_in_hours > 0:
            expires_at = datetime.now() + timedelta(hours=data.expires_in_hours)

        payload = {
            "session_id": session_id,
            "slug": slug,
            "created_by": user_id,
            "enabled": True,
            "expires_at": expires_at,
            "view_count": 0,
        }
        res = await self.mapper.create_from_dict(payload)
        await self.db.commit()
        return res

    async def list_by_session(self, session_id: str, user_id: int) -> List[SessionShare]:
        session = await SessionMapper(self.db).get_by_id(session_id)
        if not session or session.user_id != user_id:
            return []
        return await self.mapper.list_by_session(session_id)

    async def revoke(self, share_id: int, user_id: int) -> bool:
        share = await self.mapper.get_by_id(share_id)
        if not share or share.created_by != user_id:
            return False
        await self.mapper.delete_by_id(share_id)
        await self.db.commit()
        return True


async def get_public_view(slug: str) -> Optional[SharedSessionView]:
    """公开端点的入口；独立 session，校验 + 脱敏 + view_count++。"""
    async with get_db_session() as db:
        share = await SessionShareMapper(db).get_by_slug(slug)
        if not share or not share.enabled:
            return None
        if share.expires_at and share.expires_at < datetime.now():
            return None

        session = await SessionMapper(db).get_by_id(share.session_id)
        if not session:
            return None

        agent = await AgentMapper(db).get_by_id(session.agent_id)
        messages = await ChatMessageMapper(db).get_ancestor_chain(
            session_id=share.session_id,
            message_id=None,
        )

        # view_count++
        await db.execute(
            update(type(share))
            .where(type(share).id == share.id)
            .values(view_count=type(share).view_count + 1)
        )

    sanitized: List[SharedMessage] = []
    for m in messages:
        sanitized.append(
            SharedMessage(
                id=m.id,
                type=m.type,
                content=_sanitize_message_content(m),
                name=m.name,
                created_at=m.created_at,
            )
        )

    return SharedSessionView(
        slug=share.slug,
        session_title=session.title,
        agent_avatar=getattr(agent, "avatar", None) if agent else None,
        agent_description=getattr(agent, "description", None) if agent else None,
        messages=sanitized,
        created_at=share.created_at,
        expires_at=share.expires_at,
    )
