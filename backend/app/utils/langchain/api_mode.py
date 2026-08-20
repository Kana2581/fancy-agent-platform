"""OpenAI Responses protocol configuration and cross-protocol history adapters."""

from __future__ import annotations

from typing import Any, Iterable

from langchain_core.messages import BaseMessage


def model_init_kwargs(config: Any) -> dict[str, Any]:
    """Convert a ValidChatModel to kwargs accepted by ``init_chat_model``."""
    kwargs = config.model_dump(exclude={"api_mode"})
    if config.model_provider == "openai" and config.api_mode == "responses":
        # responses/v1 retains the native output-item content blocks and metadata.
        kwargs.update(use_responses_api=True, output_version="responses/v1")
    return kwargs


def visible_content(content: Any) -> Any:
    """Extract user-visible text/media from a Responses content-block payload.

    It deliberately skips reasoning blocks. Unknown blocks are ignored rather
    than stringified, preventing raw Responses JSON from leaking into the UI.
    """
    if not isinstance(content, list):
        return content
    visible: list[Any] = []
    for item in content:
        if isinstance(item, str):
            visible.append(item)
            continue
        if not isinstance(item, dict):
            continue
        kind = item.get("type", "")
        if kind in {"text", "output_text", "input_text"}:
            text = item.get("text") or item.get("content")
            if isinstance(text, str):
                visible.append(text)
        elif kind in {"image", "image_url", "input_image", "output_image"}:
            # Preserve image blocks in a form accepted by chat-completions.
            url = item.get("image_url") or item.get("url")
            if isinstance(url, str):
                visible.append({"type": "image_url", "image_url": {"url": url}})
            elif isinstance(url, dict):
                visible.append({"type": "image_url", "image_url": url})
        elif kind in {"function_call_output", "tool_result", "computer_call_output"}:
            # Tool results are meaningful context on a Responses → Chat
            # Completions switch. Keep their result, not the protocol wrapper.
            output = item.get("output") or item.get("content")
            if isinstance(output, str):
                visible.append(output)
    if not visible:
        return ""
    if all(isinstance(item, str) for item in visible):
        return "".join(visible)
    return visible


def adapt_history_for_api_mode(messages: Iterable[BaseMessage], api_mode: str) -> list[BaseMessage]:
    """Return request-only copies without changing persisted protocol records.

    Responses can replay native output items unchanged. Chat Completions cannot,
    so only its request receives an equivalent visible-content copy.
    """
    if api_mode == "responses":
        return list(messages)
    adapted: list[BaseMessage] = []
    for message in messages:
        content = getattr(message, "content", None)
        if isinstance(content, list):
            adapted.append(message.model_copy(update={"content": visible_content(content)}, deep=True))
        else:
            adapted.append(message)
    return adapted


def response_is_incomplete(message: BaseMessage) -> bool:
    metadata = getattr(message, "response_metadata", None) or {}
    status = metadata.get("status")
    return status == "incomplete" or metadata.get("incomplete") is True
