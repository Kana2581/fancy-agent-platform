from typing import List

from app.mappers.base_mapper import BaseMapper
from app.models.chat_message import ChatMessage
from app.utils.db_compat import IS_SQLITE
from sqlalchemy import text, select


class ChatMessageMapper(BaseMapper[ChatMessage]):
    model = ChatMessage
    pk_name = "id"

    async def get_last_message_by_session(
        self,
        session_id: str,
    ):
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    async def list_by_session_id(
        self,
        session_id: str,
        order_by_created: bool = True,
    ) -> List[ChatMessage]:
        stmt = select(ChatMessage).where(
            ChatMessage.session_id == session_id
        )

        if order_by_created:
            stmt = stmt.order_by(ChatMessage.created_at)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    
    async def get_ancestor_chain(
        self,
        session_id: str,
        message_id: str,
    ):
        sql = text("""
        WITH RECURSIVE ancestors AS (
            SELECT *
            FROM chat_message
            WHERE id = :message_id
            AND session_id = :session_id

            UNION ALL

            SELECT cm.*
            FROM chat_message cm
            INNER JOIN ancestors a
                ON cm.id = a.parent_id
            AND cm.session_id = :session_id
        )
        SELECT *
        FROM ancestors;
        """)
        if message_id is None:
            last_message=await self.get_last_message_by_session(session_id=session_id)
            if last_message is None:
                return []
            message_id=last_message.id
        result = await self.db.execute(
            select(ChatMessage).from_statement(sql),
            {
                "session_id": session_id,
                "message_id": message_id,
            },
        )
        messages = result.scalars().all()
        # 逆序排列，保证从 root 到 leaf
        messages.reverse()
        return messages
    async def get_descendant_chain(
        self,
        session_id: str,
        message_id: str,
    ):
        if IS_SQLITE:
            return await self._get_descendant_chain_iter(session_id, message_id)

        sql = text("""
        WITH RECURSIVE descendants AS (

            -- 第一步：选起点的最新子节点
            SELECT cm.*
            FROM LATERAL (
                SELECT *
                FROM chat_message
                WHERE parent_id = :message_id
                AND session_id = :session_id
                ORDER BY created_at DESC
                LIMIT 1
            ) cm

            UNION ALL

            -- 递归：每一步只选当前节点的最新子节点
            SELECT cm.*
            FROM descendants d
            JOIN LATERAL (
                SELECT *
                FROM chat_message
                WHERE parent_id = d.id
                AND session_id = :session_id
                ORDER BY created_at DESC
                LIMIT 1
            ) cm ON TRUE
        )

        SELECT *
        FROM descendants;
        """)

        result = await self.db.execute(
            select(ChatMessage).from_statement(sql),
            {
                "session_id": session_id,
                "message_id": message_id,
            },
        )
        return result.scalars().all()

    async def _get_descendant_chain_iter(
        self,
        session_id: str,
        message_id: str,
    ):
        """SQLite fallback: iteratively pick the newest child at each level."""
        result = []
        current_id = message_id
        while True:
            stmt = (
                select(ChatMessage)
                .where(
                    ChatMessage.parent_id == current_id,
                    ChatMessage.session_id == session_id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
            row = (await self.db.execute(stmt)).scalar_one_or_none()
            if row is None:
                break
            result.append(row)
            current_id = row.id
        return result


    async def list_siblings_by_message_id(
        self,
        session_id: str,
        message_id: str,
    ):
        # 先查当前消息
        stmt = select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.session_id == session_id,
        )
        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            return []

        # 再查同父消息（包含自己）
        stmt = select(ChatMessage).where(
            ChatMessage.parent_id == message.parent_id,
            ChatMessage.session_id == session_id,
        ).order_by(ChatMessage.created_at)

        result = await self.db.execute(stmt)
        return result.scalars().all()
    
