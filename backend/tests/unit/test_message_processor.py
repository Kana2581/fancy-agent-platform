import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.models.chat_message import ChatMessage
from app.utils.langchain.message_processor import MessageConverter, MessageProcessor


class TestMessageConverter:
    def test_human_message_to_orm(self):
        msg = HumanMessage(content="hello")
        orm = MessageConverter.message_to_orm(msg, session_id="s1", user_id=1, parent_id=None)

        assert isinstance(orm, ChatMessage)
        assert orm.type == "human"
        assert orm.session_id == "s1"
        assert orm.user_id == 1
        assert orm.parent_id is None

    def test_ai_message_to_orm(self):
        msg = AIMessage(content="response")
        orm = MessageConverter.message_to_orm(msg, session_id="s1", user_id=2, parent_id="abc")

        assert orm.type == "ai"
        assert orm.parent_id == "abc"

    def test_orm_id_is_generated(self):
        msg = HumanMessage(content="test")
        orm = MessageConverter.message_to_orm(msg, session_id="s1", user_id=1)
        assert orm.id is not None

    def test_orm_to_human_message(self):
        chat = ChatMessage(session_id="s1", user_id=1, type="human", content="hello")
        msg = MessageConverter.orm_to_message(chat)
        assert isinstance(msg, HumanMessage)
        assert msg.content == "hello"

    def test_orm_to_ai_message(self):
        chat = ChatMessage(session_id="s1", user_id=1, type="ai", content="response")
        msg = MessageConverter.orm_to_message(chat)
        assert isinstance(msg, AIMessage)
        assert msg.content == "response"

    def test_roundtrip_preserves_content(self):
        original = HumanMessage(content="round trip test")
        orm = MessageConverter.message_to_orm(original, session_id="s1", user_id=1)
        recovered = MessageConverter.orm_to_message(orm)
        assert recovered.content == "round trip test"


class TestMessageProcessor:
    def test_parent_id_chaining(self):
        processor = MessageProcessor(session_id="s1", user_id=1, parent_id="root")
        processor.add(HumanMessage(content="q1"))
        processor.add(AIMessage(content="a1"))
        processor.add(HumanMessage(content="q2"))

        orms = processor.to_orm()

        assert len(orms) == 3
        assert all(o.id is not None for o in orms)
        assert orms[0].parent_id == "root"
        assert orms[1].parent_id == orms[0].id
        assert orms[2].parent_id == orms[1].id

    def test_no_initial_parent_id(self):
        processor = MessageProcessor(session_id="s1", user_id=1)
        processor.add(HumanMessage(content="first"))
        orms = processor.to_orm()
        assert orms[0].parent_id is None

    def test_single_message_chain(self):
        processor = MessageProcessor(session_id="s1", user_id=1, parent_id="p0")
        processor.add(AIMessage(content="only"))
        orms = processor.to_orm()
        assert orms[0].parent_id == "p0"

    def test_extend_adds_messages(self):
        processor = MessageProcessor(session_id="s1", user_id=1)
        processor.extend([HumanMessage(content="a"), AIMessage(content="b")])
        assert len(processor.messages) == 2

    def test_messages_property(self):
        processor = MessageProcessor(session_id="s1", user_id=1)
        processor.add(HumanMessage(content="x"))
        assert len(processor.messages) == 1
        assert isinstance(processor.messages[0], HumanMessage)

    def test_session_id_propagated(self):
        processor = MessageProcessor(session_id="session-xyz", user_id=5)
        processor.add(HumanMessage(content="hi"))
        orms = processor.to_orm()
        assert all(o.session_id == "session-xyz" for o in orms)

    def test_user_id_propagated(self):
        processor = MessageProcessor(session_id="s1", user_id=42)
        processor.add(HumanMessage(content="hi"))
        orms = processor.to_orm()
        assert all(o.user_id == 42 for o in orms)
