from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk
from sqlalchemy.exc import IntegrityError

from app.core.logging_config import get_logger
from app.deps.db import get_db_session
from app.mappers.agent_webhook_mapper import AgentWebhookMapper
from app.mappers.telegram_conversation_mapper import TelegramConversationMapper
from app.schemas.dto.langchian import ValidAgent
from app.services.agent_service import AgentService
from app.services.chat_file_service import ChatFileService
from app.services.chat_message_service import ChatMessageService
from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.utils.langchain.agent_util import get_langchian_agent

logger = get_logger(__name__)


async def run_agent_webhook_message(
    *,
    webhook,
    content: str,
    session_title: str,
    conversation_scope: tuple[str, str] | None = None,
) -> tuple[str, str | None, str]:
    user_id = webhook.user_id
    agent_id = webhook.agent_id

    async with get_db_session() as db:
        msg_service = ChatMessageService(db)

        if conversation_scope:
            chat_id, message_thread_id = conversation_scope
            conversation_mapper = TelegramConversationMapper(db)
            conversation = await conversation_mapper.get_by_scope(
                webhook_id=webhook.id,
                chat_id=chat_id,
                message_thread_id=message_thread_id,
            )
            if conversation:
                session_id = conversation.session_id
                last_msg = await msg_service.get_last_message_in_session(session_id)
                parent_id = last_msg.id if last_msg else None
            else:
                session = await SessionService(db).create(
                    agent_id=agent_id,
                    user_id=user_id,
                    title=session_title,
                )
                session_id = session.id
                parent_id = None
                try:
                    await conversation_mapper.create_from_dict(
                        {
                            "webhook_id": webhook.id,
                            "chat_id": chat_id,
                            "message_thread_id": message_thread_id,
                            "session_id": session_id,
                        }
                    )
                    await db.commit()
                except IntegrityError:
                    await db.rollback()
                    existing = await conversation_mapper.get_by_scope(
                        webhook_id=webhook.id,
                        chat_id=chat_id,
                        message_thread_id=message_thread_id,
                    )
                    if existing:
                        session_id = existing.session_id
                        last_msg = await msg_service.get_last_message_in_session(session_id)
                        parent_id = last_msg.id if last_msg else None
        elif webhook.persistent_session_id:
            session_id = webhook.persistent_session_id
            last_msg = await msg_service.get_last_message_in_session(session_id)
            parent_id = last_msg.id if last_msg else None
        else:
            session = await SessionService(db).create(
                agent_id=agent_id,
                user_id=user_id,
                title=session_title,
            )
            session_id = session.id
            parent_id = None
            await AgentWebhookMapper(db).update_by_id(
                webhook.id, {"persistent_session_id": session_id}
            )

        human_id = str(uuid4())
        await msg_service.create_message(
            session_id=session_id,
            type="human",
            content=content,
            parent_id=parent_id,
            message_id=human_id,
            user_id=user_id,
        )

        data_dict = await AgentService(db).get_full_agent(agent_id, user_id)

    if not data_dict:
        raise ValueError("Agent not found")

    agent_data = ValidAgent.model_validate(data_dict)
    agent_state = await get_langchian_agent(agent_data, session_id=session_id)

    history = await ChatService.fetch_history(session_id=session_id, parent_id=human_id)
    async with get_db_session() as db:
        history = await ChatFileService(db).inject_files_into_messages(history, user_id=user_id)

    final_text_parts: list[str] = []
    last_ai_id: str | None = None

    async for chunk, _parent_id in ChatService().chat(
        session_id=session_id,
        user_id=user_id,
        agent=agent_state,
        messages=history,
        leaf_message_id=human_id,
    ):
        if chunk is None:
            break
        if isinstance(chunk, AIMessage) and not isinstance(chunk, AIMessageChunk):
            chunk_content = chunk.content if isinstance(chunk.content, str) else ""
            if chunk_content:
                final_text_parts.append(chunk_content)
                last_ai_id = chunk.id

    return session_id, last_ai_id, "\n\n".join(final_text_parts) if final_text_parts else ""
