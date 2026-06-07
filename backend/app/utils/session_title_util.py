import json
import re
from typing import Iterable

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage

from app.schemas.dto.langchian import ValidAgent, ValidChatModel


class SessionTitleUtil:
    PROMPT = """请根据以下首轮对话生成一个简短的会话标题。
要求：
- 只输出标题本身，不要解释
- 使用对话主要语言
- 中文 6-12 个字左右，英文 3-8 个词左右
- 不要使用引号、句号、冒号或换行

首轮对话：
{conversation_text}"""

    @staticmethod
    async def generate(agent_data: ValidAgent, messages: Iterable[BaseMessage]) -> str:
        if not agent_data.llm:
            raise ValueError("Agent 未配置 LLM")

        lines = []
        for message in messages:
            msg_type = getattr(message, "type", "")
            if msg_type == "human":
                lines.append(f"用户：{_extract_text(message.content)}")
            elif msg_type == "ai":
                lines.append(f"助手：{_extract_text(message.content)}")

        conversation_text = "\n\n".join(line for line in lines if line.strip())
        if not conversation_text:
            raise ValueError("没有可用于生成标题的首轮对话内容")

        model_config = ValidChatModel.model_validate(agent_data.llm)
        llm = init_chat_model(**model_config.model_dump())
        response = await llm.ainvoke([
            HumanMessage(
                content=SessionTitleUtil.PROMPT.format(
                    conversation_text=conversation_text,
                )
            )
        ])
        return _clean_title(response.content)


def _extract_text(content) -> str:
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return " ".join(
                    block.get("text", "") for block in parsed
                    if isinstance(block, dict) and block.get("type") == "text"
                )
        except (json.JSONDecodeError, TypeError):
            pass
        return content
    return str(content) if content else ""


def _clean_title(content) -> str:
    title = _extract_text(content).strip()
    title = re.sub(r"[\r\n]+", " ", title)
    title = title.strip(" \t\"'“”‘’`。.，,：:；;")
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        raise ValueError("模型返回了空标题")
    return title[:80]
