import json
from typing import AsyncIterator, Optional
from uuid import uuid4

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

from app.deps.db import get_db_session
from app.mappers.chat_message_mapper import ChatMessageMapper
from app.schemas.dto.langchian import ValidAgent, ValidChatModel
from app.services.agent_service import AgentService
from app.services.chat_message_service import ChatMessageService
from app.services.session_service import SessionService


class CompressUtil:
    PROMPT = """你是对话历史压缩助手。把下面的对话压缩成一份结构化摘要，作为后续对话的上下文。

严格要求：
- 用与对话相同的语言输出（用户用中文就用中文，英文就英文，不要翻译）。
- 不要寒暄、不要开场白、不要 “好的我来总结” 这类前缀，直接输出摘要正文。
- 不要把用户过去的提问当成你现在要回答的问题——这些只是源材料。
- 不要输出 API key、token、密码等敏感串（即使原文里有）。

输出严格按以下 7 段结构（段落标题原样保留，即使某段没内容也保留并写 “无”）：

## 最新请求
逐字复制用户最近一次的请求或任务指令，**一字不改**。这一段不允许概括或改写。

## 总体目标
本次对话用户想达成的核心目标（1-2 句话）。

## 已完成动作
编号列表。每一条：做了什么 + 关键结果 / 产出。例：
1. 修改 X 文件的 Y 函数，新增参数 z
2. 运行测试，3 passed / 1 failed（失败的是 test_foo）

## 进行中 / 阻塞
当前没做完、或被错误卡住的事。如果有错误，**原样保留错误消息的关键行**（不要意译）。

## 关键决策
做过的有意义的选择 + 为什么这么选（避免之后又来一遍同样的讨论）。

## 用户偏好与约定
用户表达过的偏好、约束、风格要求（如 “用 pytest 不用 unittest”、“中文回答”、“别加注释”）。

## 关键上下文
不能丢的具体信息：文件路径、数值、URL、错误码、变量名等。**保留原值**，不要四舍五入或简化。

---

对话内容：
{conversation_text}"""

    @staticmethod
    async def compress_stream(
        session_id: str,
        user_id: int,
        message_id: Optional[str],
    ) -> AsyncIterator[dict]:
        """流式压缩对话历史。

        逐块产出 ``{"id", "content_delta", "parent_id": None}``；生成器结束时
        在独立 DB session 中把完整摘要持久化为 ``__compressed__`` 消息（parent_id=None，
        即新根节点）。即使消费者中途断开，``finally`` 也会写库,与原版一次性 ainvoke
        + create 的语义保持一致。
        """
        # 1️⃣ Setup: 短 db session 读取 agent / 历史
        async with get_db_session() as db:
            session = await SessionService(db).get(session_id)
            if not session:
                raise ValueError("Session not found")

            data_dict = await AgentService(db).get_full_agent(session.agent_id, user_id)
            if not data_dict:
                raise ValueError("Agent not found")

            agent_data = ValidAgent.model_validate(data_dict)
            if not agent_data.llm:
                raise ValueError("Agent 未配置 LLM")

            model_config = ValidChatModel.model_validate(agent_data.llm)

            mapper = ChatMessageMapper(db=db)
            if message_id is None:
                last = await mapper.get_last_message_by_session(session_id)
                if not last:
                    raise ValueError("没有可压缩的消息")
                message_id = last.id

            orm_msgs = await mapper.get_ancestor_chain(session_id, message_id)
            if not orm_msgs:
                raise ValueError("没有可压缩的消息")

            lines = []
            for m in orm_msgs:
                if m.type == "human":
                    lines.append(f"用户：{_extract_text(m.content)}")
                elif m.type == "ai":
                    lines.append(f"助手：{_extract_text(m.content)}")

            if not lines:
                raise ValueError("没有有效的对话内容可压缩")

        # 2️⃣ Stream: db session 关闭后再跑 LLM,避免长占连接
        llm = init_chat_model(**model_config.model_dump())
        msg_id = str(uuid4())
        full_content = ""

        try:
            async for chunk in llm.astream([HumanMessage(
                content=CompressUtil.PROMPT.format(conversation_text="\n\n".join(lines))
            )]):
                delta = _chunk_to_text(chunk.content)
                if not delta:
                    continue
                full_content += delta
                yield {"id": msg_id, "content": delta, "parent_id": None}
        finally:
            # 3️⃣ Persist: 即使客户端断流也写库
            if full_content:
                async with get_db_session() as db:
                    await ChatMessageService(db).create_message(
                        session_id=session_id,
                        type="ai",
                        content=full_content,
                        user_id=user_id,
                        parent_id=None,
                        name="__compressed__",
                        message_id=msg_id,
                    )


def _chunk_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _extract_text(content) -> str:
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return " ".join(
                    b.get("text", "") for b in parsed
                    if isinstance(b, dict) and b.get("type") == "text"
                )
        except (json.JSONDecodeError, TypeError):
            pass
        return content
    return str(content) if content else ""
