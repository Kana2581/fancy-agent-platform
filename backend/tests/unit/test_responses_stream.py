from langchain_core.messages import AIMessage, AIMessageChunk

from app.services.chat_service import ChatService


class _ResponsesLikeAgent:
    """Responses-style stream: only the created event has the stable response ID."""

    async def astream(self, **_kwargs):
        yield "messages", (AIMessageChunk(id="resp-1", content=[]), {})
        yield "messages", (
            AIMessageChunk(
                id="langgraph-generated-id-1",
                content=[{"type": "text", "text": "same response"}],
            ),
            {},
        )
        yield "messages", (
            AIMessageChunk(
                id="langgraph-generated-id-2",
                content=[{"type": "text", "text": " continued"}],
            ),
            {},
        )
        yield "updates", {
            "model": {
                "messages": [
                    AIMessage(
                        id="resp-1",
                        content=[{"type": "text", "text": "same response continued"}],
                    )
                ]
            }
        }


async def test_responses_stream_uses_one_stable_message_id(monkeypatch):
    persisted = []

    async def fake_persist(processor):
        persisted.extend(processor.messages)

    monkeypatch.setattr(ChatService, "_persist", staticmethod(fake_persist))

    events = [
        event
        async for event in ChatService().chat(
            session_id="session-1",
            user_id=1,
            agent=_ResponsesLikeAgent(),
            messages=[],
            leaf_message_id="human-1",
        )
    ]

    emitted = [message for message, _parent_id in events if message is not None]
    assert [message.id for message in emitted] == ["resp-1", "resp-1", "resp-1"]
    assert isinstance(emitted[-1], AIMessage)
    assert len(persisted) == 1
    assert persisted[0].id == "resp-1"
