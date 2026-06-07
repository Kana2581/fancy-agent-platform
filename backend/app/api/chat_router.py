from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.deps.db import get_db_session
from app.deps.user import get_current_user
from app.services.agent_service import AgentService
from app.services.chat_file_service import ChatFileService
from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.schemas.dto.langchian import ValidAgent
from app.schemas.chat_schema import ChatRequest, SimpleFile, CompressRequest, ApproveToolRequest
import json
from langchain_core.messages import message_to_dict, HumanMessage, ToolMessage, AIMessage
from langchain_core.messages.utils import convert_to_openai_messages, messages_from_dict
from app.utils.langchain.agent_util import get_langchian_agent, get_langchain_agent_and_tools
from app.utils.langchain.message_processor import MessageProcessor
from langgraph.prebuilt import ToolNode
from uuid import uuid4
from app.mappers.message_approval_mapper import MessageApprovalMapper
from app.utils.session_title_util import SessionTitleUtil

from fastapi import Depends, HTTPException
from app.schemas.chat_schema import ChatResponse

from typing import AsyncIterator, List, Optional
from fastapi import Path, Query
from app.deps.service import get_chat_message_service, get_chat_file_service, get_session_service
from app.services.chat_message_service import ChatMessageService

from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def format_sse(event: dict, event_type: str = "message") -> str:
    return (
        f"event: {event_type}\n"
        f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    )


def format_error_sse(code: str, message: str) -> str:
    return format_sse({"code": code, "message": message}, "error")


async def _stream_agent_response(
    chat_service: ChatService,
    *,
    session_id: str,
    user_id: int,
    agent,
    messages,
    leaf_message_id: str | None,
    emit_done: bool = True,
) -> AsyncIterator[str]:
    """共享流式循环 + interrupt 处理。"""
    last_ai_msg_id = None
    async for chunk, parent_message_id in chat_service.chat(
        session_id=session_id,
        user_id=user_id,
        agent=agent,
        messages=messages,
        leaf_message_id=leaf_message_id,
    ):
        if chunk is None and parent_message_id == "__interrupt__":
            if not last_ai_msg_id:
                yield "event: done\ndata: {}\n\n"
                return
            async with get_db_session() as db:
                approval_mapper = MessageApprovalMapper(db)
                await approval_mapper.create_pending(last_ai_msg_id)
            yield format_sse({"message_id": last_ai_msg_id}, "tool_approval_required")
            return

        chunk_data = message_to_dict(chunk)
        chunk_data["data"]["parent_id"] = parent_message_id
        if chunk_data.get("type") in ("ai", "AIMessageChunk"):
            last_ai_msg_id = chunk_data.get("data", {}).get("id")
        yield format_sse(chunk_data)

    if emit_done:
        yield "event: done\ndata: {}\n\n"


@router.post("/{session_id}/stream")
async def chat_stream(
    session_id: str,
    body: ChatRequest,
    user_id: int = Depends(get_current_user),
):
    parent_id = body.parent_id

    async def event_generator():
        try:
            async with get_db_session() as db:
                session_service = SessionService(db)
                agent_service = AgentService(db)
                chat_message_service = ChatMessageService(db)

                # 1️⃣ 校验 parent message
                if parent_id:
                    parent_message = await chat_message_service.get_message(parent_id)
                    if not parent_message:
                        logger.error(f"Parent message not found: {parent_id}")
                        yield format_error_sse("PARENT_MESSAGE_NOT_FOUND", "父消息不存在")
                        yield "event: done\ndata: {}\n\n"
                        return

                # 2️⃣ 获取 session 并校验归属
                session = await session_service.get(session_id)
                if not session or session.user_id != user_id:
                    logger.error(f"Session not found or access denied: {session_id}")
                    yield format_error_sse("SESSION_NOT_FOUND", "会话不存在或无访问权限")
                    yield "event: done\ndata: {}\n\n"
                    return
                agent_id = session.agent_id

                # 3️⃣ 获取 agent 数据
                data_dict = await agent_service.get_full_agent(agent_id, user_id)

            agent_data = ValidAgent.model_validate(data_dict)
            agent_state = await get_langchian_agent(agent_data, session_id=session_id)
            should_auto_title = False

            if body.content and body.id:
                # 1. 新消息直接存 DB
                async with get_db_session() as db:
                    session_service = SessionService(db)
                    chat_message_service = ChatMessageService(db)
                    chat_file_service = ChatFileService(db)
                    session = await session_service.get(session_id)
                    existing_last = await chat_message_service.get_last_message_in_session(session_id)
                    should_auto_title = bool(
                        session
                        and body.parent_id is None
                        and existing_last is None
                        and not getattr(session, "auto_title_generated", False)
                    )
                    await chat_message_service.create_message(
                        session_id=session_id,
                        type="human",
                        content=body.content,
                        parent_id=body.parent_id,
                        message_id=body.id,
                        user_id=user_id,
                    )
                    await chat_file_service.attach_files_to_message(
                        message_id=body.id,
                        file_ids=body.file_ids or [],
                    )

            # 2. 查祖先链（新消息已在链上）
            history = await ChatService.fetch_history(
                session_id=session_id,
                parent_id=body.id or body.parent_id,
            )

            # 2b. 检查祖先链中是否有未审批的工具调用
            ancestor_ids = [m.id for m in history if m.id]
            async with get_db_session() as db:
                approval_mapper = MessageApprovalMapper(db)
                pending = await approval_mapper.get_pending_by_message_ids(ancestor_ids)
            if pending:
                yield format_sse({"message_id": pending.message_id}, "tool_approval_required")
                yield "event: done\ndata: {}\n\n"
                return

            # 3. 统一注入文件内容
            async with get_db_session() as db:
                chat_file_service = ChatFileService(db)
                messages_with_files = await chat_file_service.inject_files_into_messages(
                    history,
                    user_id=user_id,
                )

            # 4. 推理
            stream_emitted_done = False
            stream_needs_approval = False
            async for sse in _stream_agent_response(
                ChatService(),
                session_id=session_id,
                user_id=user_id,
                agent=agent_state,
                messages=messages_with_files,
                leaf_message_id=body.id or body.parent_id,
                emit_done=False,
            ):
                if sse.startswith("event: done"):
                    stream_emitted_done = True
                elif sse.startswith("event: tool_approval_required"):
                    stream_needs_approval = True
                yield sse

            if should_auto_title and not stream_emitted_done and not stream_needs_approval:
                generated_title = None
                try:
                    title_history = await ChatService.fetch_history(
                        session_id=session_id,
                        parent_id=None,
                    )
                    generated_title = await SessionTitleUtil.generate(agent_data, title_history)
                except Exception as e:
                    logger.warning(f"Auto title generation failed for session {session_id}: {e}")

                try:
                    async with get_db_session() as db:
                        await SessionService(db).mark_auto_title_attempted(
                            session_id=session_id,
                            title=generated_title,
                        )
                    if generated_title:
                        yield format_sse(
                            {"session_id": session_id, "title": generated_title},
                            "session_title",
                        )
                except Exception as e:
                    logger.exception(f"Auto title persistence failed for session {session_id}: {e}")

            if not stream_emitted_done and not stream_needs_approval:
                yield "event: done\ndata: {}\n\n"

        except Exception as e:
            logger.exception(f"Stream error in session {session_id}: {e}")
            yield format_error_sse("STREAM_ERROR", f"推理过程中发生错误：{str(e)}")
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{session_id}/approve-tool")
async def approve_tool(
    session_id: str,
    body: ApproveToolRequest,
    user_id: int = Depends(get_current_user),
):
    async def event_generator():
        try:
            # Load session and agent config
            async with get_db_session() as db:
                session_service = SessionService(db)
                agent_service = AgentService(db)

                session = await session_service.get(session_id)
                if not session or session.user_id != user_id:
                    yield format_error_sse("SESSION_NOT_FOUND", "会话不存在或无访问权限")
                    yield "event: done\ndata: {}\n\n"
                    return

                data_dict = await agent_service.get_full_agent(session.agent_id, user_id)

            agent_data = ValidAgent.model_validate(data_dict)

            # Update approval status in DB
            new_status = "approved" if body.approved else "rejected"
            async with get_db_session() as db:
                approval_mapper = MessageApprovalMapper(db)
                await approval_mapper.update_status(body.message_id, new_status)

            # Fetch history up to and including the interrupted AI message (approved & rejected 都需要)
            history = await ChatService.fetch_history(session_id, parent_id=body.message_id)

            async with get_db_session() as db:
                chat_file_service = ChatFileService(db)
                history = await chat_file_service.inject_files_into_messages(
                    history,
                    user_id=user_id,
                )

            ai_msg = history[-1]

            if not isinstance(ai_msg, AIMessage):
                ai_msg = messages_from_dict([ai_msg])[0]

            if not getattr(ai_msg, "tool_calls", None):
                yield "event: done\ndata: {}\n\n"
                return

            # Build agent + tools
            agent, tools = await get_langchain_agent_and_tools(agent_data, session_id=session_id)

            if body.approved:
                # Execute all pending tool calls
                tools_by_name = {tool.name: tool for tool in tools}
                tool_results = []
                for tool_call in ai_msg.tool_calls:
                    tool = tools_by_name[tool_call["name"]]
                    observation = await tool.ainvoke(tool_call["args"])
                    tool_results.append(
                        ToolMessage(
                            content=observation,
                            tool_call_id=tool_call["id"],
                            id=str(uuid4()),
                        )
                    )
            else:
                # ✅ 拒绝：为每个 tool_call 伪造一条拒绝的 ToolMessage
                tool_results = []
                for tool_call in ai_msg.tool_calls:
                    reject_content = "用户拒绝了该工具调用。"

                    tool_results.append(
                        ToolMessage(
                            content=reject_content,
                            tool_call_id=tool_call["id"],
                            id=str(uuid4()),
                        )
                    )

            # Persist tool messages chained from AI message (approved & rejected 统一处理)
            processor = MessageProcessor(
                session_id=session_id,
                user_id=user_id,
                parent_id=body.message_id,
            )
            for tm in tool_results:
                processor.add(tm)
            await ChatService._persist(processor)

            # Yield tool messages as SSE
            current_parent = body.message_id
            for tm in tool_results:
                tm_dict = message_to_dict(tm)
                tm_dict["data"]["parent_id"] = current_parent
                yield format_sse(tm_dict)
                current_parent = tm.id

            leaf_id = tool_results[-1].id
            all_messages = history + tool_results

            # Resume streaming from the agent with full history (approved & rejected 都继续让 agent 回复)
            async for sse in _stream_agent_response(
                ChatService(),
                session_id=session_id,
                user_id=user_id,
                agent=agent,
                messages=all_messages,
                leaf_message_id=leaf_id,
            ):
                yield sse

        except Exception as e:
            logger.exception(f"Approve tool stream error in session {session_id}: {e}")
            yield format_error_sse("TOOL_EXECUTION_ERROR", f"工具执行过程中发生错误：{str(e)}")
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get(
    "/sessions/{session_id}/chain-to-root",
    response_model=List[ChatResponse],
)
async def get_message_chain_to_root(
    session_id: str = Path(...),
    message_id: Optional[str] = Query(
        None,
        description="起始 message_id，不传则使用 session 最后一条消息",
    ),
    service: ChatMessageService = Depends(get_chat_message_service),
    session_service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    session = await session_service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return await service.get_message_chain_to_root(
        session_id=session_id,
        message_id=message_id,
    )


@router.get(
    "/{message_id}/descendants",
    response_model=List[ChatResponse],
)
async def get_descendants(
    message_id: str = Path(...),
    session_id: str = Query(...),
    service: ChatMessageService = Depends(get_chat_message_service),
    session_service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    session = await session_service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return await service.get_descendants(
        session_id=session_id,
        message_id=message_id,
    )


@router.get(
    "/{message_id}/siblings",
    response_model=List[ChatResponse],
)
async def get_siblings(
    message_id: str = Path(...),
    session_id: str = Query(...),
    service: ChatMessageService = Depends(get_chat_message_service),
    session_service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    session = await session_service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return await service.get_siblings(
        session_id=session_id,
        message_id=message_id,
    )


@router.post("/{session_id}/compress")
async def compress_session(
    session_id: str,
    body: CompressRequest,
    user_id: int = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    session = await session_service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    from app.utils.compress_util import CompressUtil

    async def event_generator():
        try:
            async for chunk in CompressUtil.compress_stream(
                session_id=session_id,
                user_id=user_id,
                message_id=body.message_id,
            ):
                payload = {
                    "type": "AIMessageChunk",
                    "data": {
                        "id": chunk["id"],
                        "content": chunk["content"],
                        "parent_id": chunk["parent_id"],
                    },
                }
                yield format_sse(payload)
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            logger.exception(f"Compress error in session {session_id}: {e}")
            yield format_error_sse("COMPRESS_ERROR", f"压缩失败：{str(e)}")
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{session_id}/export")
async def export_message_chain(
    session_id: str = Path(...),
    message_id: Optional[str] = Query(None, description="导出到该消息为止的祖先链，不传则使用最后一条消息"),
    session_service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    session = await session_service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await ChatService.fetch_history(session_id=session_id, parent_id=message_id)
    openai_messages = convert_to_openai_messages(messages)
    return {"messages": openai_messages}


@router.get("/{session_id}/messages", response_model=List[ChatResponse])
async def get_session_messages(
    session_id: str = Path(...),
    chat_message_service: ChatMessageService = Depends(get_chat_message_service),
    chat_file_service: ChatFileService = Depends(get_chat_file_service),
    session_service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    session = await session_service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    messages_orm = await chat_message_service.list_messages_by_session(session_id=session_id)
    messages: List[ChatResponse] = [
        ChatResponse.model_validate(message, from_attributes=True) for message in messages_orm
    ]

    human_ids = [m.id for m in messages if m.type == "human"]
    if human_ids:
        file_maps = await chat_file_service.get_files_map_by_message_ids(human_ids)
        for m in messages:
            if m.type == "human":
                files = file_maps.get(m.id, None)
                if files:
                    m.files = [SimpleFile.model_validate(file, from_attributes=True) for file in files]

    # Inject approval_status for AI messages that have a tool approval record
    all_ids = [m.id for m in messages]
    async with get_db_session() as db:
        approval_mapper = MessageApprovalMapper(db)
        approvals = await approval_mapper.get_by_message_ids(all_ids)
    approval_map = {a.message_id: a.status for a in approvals}
    for m in messages:
        if m.id in approval_map:
            m.approval_status = approval_map[m.id]

    return messages
