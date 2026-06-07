import uuid
from typing import List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, message_to_dict
from sqlalchemy import inspect
from app.models.chat_message import ChatMessage


class MessageConverter:
    @staticmethod
    def message_to_orm(
        message: BaseMessage,
        *,
        session_id: str,
        user_id:int,
        parent_id: Optional[str] = None,
    ) -> ChatMessage:
        msg_dict = message_to_dict(message)
        data = msg_dict.get("data", {})

        orm_columns = {c.key for c in inspect(ChatMessage).mapper.column_attrs}

        payload = {k: v for k, v in data.items() if k in orm_columns}
        payload.update(
            {
                "session_id": session_id,
                "parent_id": parent_id,
                "user_id": user_id,
            }
        )
        if not payload.get("id"):
            payload["id"] = str(uuid.uuid4())
        return ChatMessage(**payload)

    @staticmethod
    def orm_to_message(chat: ChatMessage) -> BaseMessage:
        data = {
            c.key: getattr(chat, c.key)
            for c in inspect(ChatMessage).mapper.column_attrs
            if getattr(chat, c.key) is not None
        }

        type_ = (data.pop("type", "human") or "human").lower()

        mapping = {
            "human": HumanMessage,
            "ai": AIMessage,
            "tool": ToolMessage,
        }

        cls = mapping.get(type_, BaseMessage)
        return cls(**data)


class MessageProcessor:
    def __init__(
        self,
        *,
        session_id: str,
        user_id: int,
        parent_id: Optional[str] = None,
    ):
        self.session_id = session_id
        self.parent_id = parent_id
        self.user_id = user_id
        self._messages: list[BaseMessage] = []

    def add(self, message: BaseMessage) -> None:
        self._messages.append(message)

    def extend(self, messages: list[BaseMessage]) -> None:
        self._messages.extend(messages)

    @property
    def messages(self) -> list[BaseMessage]:
        return self._messages

    def to_orm(self) -> list[ChatMessage]:
        orm_messages: list[ChatMessage] = []

        current_parent_id = self.parent_id

        for msg in self._messages:
            orm = MessageConverter.message_to_orm(
                msg,
                session_id=self.session_id,
                user_id=self.user_id,
                parent_id=current_parent_id,
            )

            orm_messages.append(orm)

            # ⭐ 核心：下一个消息的 parent = 当前消息的 id
            current_parent_id = orm.id

        return orm_messages


