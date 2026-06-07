from typing import Callable, Any, override

from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, hook_config, before_model, AgentMiddleware
from langchain_core.messages import trim_messages, RemoveMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import interrupt, Command

from app.utils.text_file import clean_and_truncate_content


class ToolCallInterruptMiddleware(AgentMiddleware):
    def __init__(self,human_in_the_loop):
        self.human_in_the_loop = human_in_the_loop

    def wrap_tool_call(
            self,
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        if self.human_in_the_loop and request:
            return interrupt("human in the loop")
        result = handler(request)
        return result


    async def awrap_tool_call(
            self,
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        if self.human_in_the_loop and request:
            return interrupt("human in the loop")
        result = handler(request)
        return result


class MessageLimitMiddleware(AgentMiddleware):
    def __init__(self,max_token_size):
        self.max_token_size = max_token_size
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not self.max_token_size:
            return None
        messages=state["messages"]
        for message in messages:
            if message.type=="tool":
                message.content=clean_and_truncate_content(message.content)
        new_messages = trim_messages(
            messages = messages,
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=self.max_token_size,
            start_on="human",
            include_system=True,
        )

        # Guard: if trimming removed all messages, skip the update to avoid
        # sending empty messages to the LLM (Anthropic requires at least one user message)
        has_human = any(getattr(m, "type", None) == "human" for m in new_messages)
        if not has_human:
            return None

        return {
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                *new_messages
            ]
        }
