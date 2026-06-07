# app/services/chat_message_service.py

from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.chat_message_mapper import ChatMessageMapper
from app.models.chat_message import ChatMessage


class ChatMessageService:
    def __init__(self, db : AsyncSession):
        self.db = db
        self.mapper = ChatMessageMapper(db=db)

    # =========================================================
    # 查询
    # =========================================================

    async def get_message(self, message_id: str) -> Optional[ChatMessage]:
        return await self.mapper.get_by_id(message_id)

    async def list_messages_by_session(
        self,
        session_id: str,
    ) -> List[ChatMessage]:
        """
        查询某个 session 下的所有消息（按时间升序）
        """
        return await self.mapper.list_by_session_id(session_id)

    async def get_last_message_in_session(
        self,
        session_id: str,
    ) -> Optional[ChatMessage]:
        """
        获取 session 中按时间最后一条消息
        """
        return await self.mapper.get_last_message_by_session(session_id)

    # ---------------------------------------------------------
    # 树结构查询
    # ---------------------------------------------------------

    async def get_message_chain_to_root(
        self,
        session_id: str,
        message_id: Optional[str] = None,
    ) -> List[ChatMessage]:
        """
        从指定 message 开始，一路向上追溯到 root

        如果 message_id 为空：
            自动使用 session 中最后一条消息

        返回顺序：root -> leaf
        """

        # 1. 如果没传 message_id，找 session 最后消息
        if message_id is None:
            last_message = await self.get_last_message_in_session(session_id)
            if not last_message:
                return []
            message_id = last_message.id

        # 2. 校验 message 是否存在 & 属于该 session
        message = await self.mapper.get_by_id(message_id)
        if not message or message.session_id != session_id:
            return []

        # 3. 查询祖先链
        messages = await self.mapper.get_ancestor_chain(
            session_id=session_id,
            message_id=message_id,
        )

        # 4. root -> leaf 排序
        # messages.sort(key=lambda m: m.created_at)
  
        return messages

    async def get_descendants(
        self,
        session_id: str,
        message_id: str,
    ) -> List[ChatMessage]:
        """
        获取某条消息的所有子孙（不包含自己）
        """
        return await self.mapper.get_descendant_chain(
            session_id=session_id,
            message_id=message_id,
        )

    async def get_siblings(
        self,
        session_id: str,
        message_id: str,
    ) -> List[ChatMessage]:
        """
        获取同 parent 的所有消息（包含自己）
        """
        return await self.mapper.list_siblings_by_message_id(
            session_id=session_id,
            message_id=message_id,
        )

    # =========================================================
    # 新增
    # =========================================================

    async def create_message(
        self,
        session_id: str,
        type: str,
        content: str,
        user_id: int,
        *,
        message_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        tool_calls: Optional[dict] = None,
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,
        message_group_id: Optional[str] = None,

    ) -> ChatMessage:
        """
        创建一条聊天消息
        """

        data = {
            "session_id": session_id,
            "parent_id": parent_id,
            "id": message_id,
            "type": type,

            "tool_calls": tool_calls,
            "tool_call_id": tool_call_id,
            "name": name,
            "message_group_id": message_group_id,
            "user_id": user_id,
            "content": content,
        }

        res = await self.mapper.create_from_dict(data)
        await self.db.commit()
        return res

    
    async def bulk_create_messages(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        *,
        parent_id: Optional[str] = None,
    ) -> List[ChatMessage]:
        """
        批量创建消息

        messages 示例：
        [
            {"type": "user", "artifact": "hi"},
            {"type": "assistant", "artifact": "hello"}
        ]
        """

        data_list = []

        for msg in messages:
            data_list.append({
                "session_id": session_id,
                "parent_id": msg.get("parent_id", parent_id),
                "type": msg["type"],
                "artifact": msg.get("artifact"),
                "tool_calls": msg.get("tool_calls"),
                "tool_call_id": msg.get("tool_call_id"),
                "name": msg.get("name"),
                "message_group_id": msg.get("message_group_id"),
            })

        res = await self.mapper.bulk_create_from_dicts(data_list)

        await self.db.commit()
        return res

    # =========================================================
    # 删除
    # =========================================================

    async def delete_message(self, message_id: str) -> bool:
        """
        删除单条消息（子消息是否级联由 DB 约束决定）
        """
        res = await self.mapper.delete_by_id(message_id)
        await self.db.commit()
        return res
