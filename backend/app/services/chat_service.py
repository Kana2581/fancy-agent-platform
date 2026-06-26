import asyncio
import re
from typing import List, AsyncGenerator, Tuple, Optional, Dict

from langchain_core.messages import BaseMessage, ToolMessage, AIMessage, AIMessageChunk
from langchain_core.messages.utils import message_chunk_to_message
from langgraph.graph.state import CompiledStateGraph

from app.deps.db import get_db_session
from app.mappers.chat_message_mapper import ChatMessageMapper
from app.models.chat_message import ChatMessage
from app.utils.langchain.message_processor import MessageProcessor, MessageConverter
from app.core.logging_config import get_logger
from contextlib import nullcontext
from app.core.config import settings
from app.utils.mlflow_tracer import chat_tracing_context
logger=get_logger(__name__)
class ChatService:
    """
    职责：
      1. 将已组装好的 history_messages + new_message 送入 agent 流式推理
      2. 收集推理产物并持久化

    不再负责：
      - 查询历史消息（由 router/caller 完成）
      - 拼装文件内容（由 router/caller 完成）
      - 持有 mapper 实例变量（并发不安全）
    """

    # ------------------------------------------------------------------
    # 历史消息查询（静态工具方法，供 router 调用）
    # ------------------------------------------------------------------

    @staticmethod
    async def fetch_history(
            session_id: str,
            parent_id: Optional[str],
    ) -> List[BaseMessage]:
        """
        查询祖先链并转为 LangChain BaseMessage 列表。
        使用独立的 db session，避免与外部 session 生命周期耦合。
        """
        async with get_db_session() as db:
            mapper = ChatMessageMapper(db)
            orm_messages: List[ChatMessage] = await mapper.get_ancestor_chain(
                session_id=session_id,
                message_id=parent_id,
            )
            # 在 session 内完成转换，避免 lazy-load 问题
            return [MessageConverter.orm_to_message(m) for m in orm_messages]

    # ------------------------------------------------------------------
    # 核心推理流
    # ------------------------------------------------------------------

    async def chat(
            self,
            session_id: str,
            user_id: int,
            agent: CompiledStateGraph,
            messages: List[BaseMessage],
            leaf_message_id: str,
    ):

        _trace_ctx = (
            chat_tracing_context(session_id, str(user_id))
            if settings.MLFLOW_ENABLED
            else nullcontext()
        )

        parent_id = leaf_message_id
        now_id = None

        processor = MessageProcessor(
            session_id=session_id,
            user_id=user_id,
            parent_id=parent_id,
        )

        # 按 msg.id 缓存流式 AI chunk，客户端中途打断时用于合并落库
        chunk_buffer: Dict[str, List[AIMessageChunk]] = {}

        def update_parent(res):
            nonlocal now_id, parent_id

            # 第一次 or 新 message

            if now_id is None:
                now_id = res.id
            if now_id != res.id:
                parent_id = now_id
                now_id =res.id


        try:
            with _trace_ctx:
                async for update_type, chunk in agent.astream(
                        input={"messages": messages},
                        stream_mode=["messages", "updates"],
                ):

                    # =====================
                    # messages
                    # =====================
                    if update_type == "messages":
                        msg, meta = chunk

                        if not isinstance(msg, ToolMessage) and msg.id != "__remove_all__":
                            # 当检测到新消息 ID 时（上一条已结束、进入下一条），
                            # 及时更新 parent_id，避免 AIMessageChunk 携带错误的父节点。

                            if now_id is None:
                                now_id = msg.id
                            elif now_id != msg.id:
                                parent_id = now_id
                                now_id = msg.id

                            if isinstance(msg, AIMessageChunk) and msg.id:
                                chunk_buffer.setdefault(msg.id, []).append(msg)

                            yield msg, parent_id

                    # =====================
                    # updates
                    # =====================
                    elif update_type == "updates":

                        if "tools" in chunk:
                            res = chunk["tools"]["messages"][-1]
                            update_parent(res)
                            processor.add(res)
                            yield res, parent_id

                        elif "model" in chunk:
                            res = chunk["model"]["messages"][-1]
                            update_parent(res)
                            # 模型完整产出，对应 chunk 缓存作废
                            if getattr(res, "id", None):
                                chunk_buffer.pop(res.id, None)
                            processor.add(res)
                            logger.info(f"{res}")
                            yield res, parent_id

                        elif "__interrupt__" in chunk:
                            # Human-in-the-loop：立刻持久化已产出消息，确保 router 随后写
                            # MessageApproval、以及客户端调用 /approve-tool 时 AI 消息已经落库。
                            await self._persist(processor)
                            processor._messages.clear()
                            chunk_buffer.clear()  # 完整产出的 AI 消息对应的 chunk 不再需要
                            yield None, "__interrupt__"
                            return
        finally:
            # 兜底路径：正常跑完 / 客户端 abort（CancelledError/GeneratorExit）。
            # tool-approval interrupt 已在上面提前 persist+clear，这里 processor 为空、buffer 也被清空，无副作用。
            if chunk_buffer:
                self._flush_interrupted_chunks(chunk_buffer, processor)
            self._inject_image_markdown(processor)
            # 客户端 abort 时当前任务已被取消，直接 await 会让 _persist 里
            # 每一步 DB await 立刻再抛 CancelledError，部分消息根本写不进库。
            # shield 让持久化作为独立子任务跑完；外层 await 仍会被取消，但无所谓——
            # 我们只在乎写库完成，不需要拿到返回值。
            await asyncio.shield(self._persist(processor))
    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    @staticmethod
    async def _persist(processor: MessageProcessor) -> None:
        new_orm_messages = processor.to_orm()
        if not new_orm_messages:
            return
        async with get_db_session() as db:
            mapper = ChatMessageMapper(db)
            await mapper._bulk_create_entities(new_orm_messages)

    @staticmethod
    def _flush_interrupted_chunks(
        buffer: Dict[str, List[AIMessageChunk]],
        processor: MessageProcessor,
    ) -> None:
        """
        客户端中途 abort 时，AI 消息没等到 updates["model"] 就断流了。
        把 buffer 里残留的 chunk 合并成一条 AIMessage 补进 processor。

        打断时 tool_call 的 args JSON 很可能不完整（test_chunk_merge 场景4），
        保留会让下一轮 LLM 因找不到对应 ToolMessage 报错，直接剥离。
        纯工具调用被打断、无任何文本时 → 跳过，不落空消息。
        """
        for msg_id, chunks in buffer.items():
            if not chunks:
                continue
            merged = message_chunk_to_message(sum(chunks[1:], chunks[0]))
            if getattr(merged, "tool_calls", None):
                merged.tool_calls = []
            if getattr(merged, "tool_call_chunks", None):
                merged.tool_call_chunks = []
            if getattr(merged, "invalid_tool_calls", None):
                merged.invalid_tool_calls = []
            if not merged.content:
                continue
            processor.add(merged)

    @staticmethod
    def _inject_image_markdown(processor: "MessageProcessor") -> None:
        """Ensure any image URLs produced by tool calls appear as markdown in the following AI message.

        Runs before persist so that chat history always shows inline images even if the LLM
        chose not to include the markdown syntax in its streamed response.
        """
        _URL_PATTERNS = [
            re.compile(r'!\[.*?\]\((https?://\S+?)\)'),
            re.compile(r'URL:\s*(https?://\S+)'),
        ]

        pending_urls: list[str] = []

        for msg in processor._messages:
            if isinstance(msg, ToolMessage):
                content_str = msg.content if isinstance(msg.content, str) else ""
                for pattern in _URL_PATTERNS:
                    for match in pattern.finditer(content_str):
                        url = match.group(1).rstrip(')')
                        if url not in pending_urls:
                            pending_urls.append(url)
            elif isinstance(msg, AIMessage) and pending_urls:
                missing = [u for u in pending_urls if u not in (msg.content if isinstance(msg.content, str) else "")]
                if missing:
                    markdown_suffix = "\n\n" + "\n\n".join(f"![Generated Image]({u})" for u in missing)
                    if isinstance(msg.content, str):
                        msg.content = msg.content + markdown_suffix
                    elif isinstance(msg.content, list):
                        msg.content = list(msg.content) + [{"type": "text", "text": markdown_suffix.strip()}]
                pending_urls = []