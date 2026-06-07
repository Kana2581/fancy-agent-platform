"""Coverage for the inline image-id injection (就地编号).

Replaces the old "append one big reference table to the last HumanMessage"
behaviour: each image is numbered in place where it appears — attachment
images get a trailing text marker, generated-image markdown gets its alt
rewritten — and ids stay stable within a session.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.core.config import settings
from app.models.chat_file import ChatFile
from app.models.chat_message_file import ChatMessageFile
from app.schemas.dto.file_message import ChatFileWithContent
from app.services.chat_file_service import ChatFileService
from app.utils.langchain.image_reference_context import (
    get_image_references,
    resolve_image_ref_id,
)
from app.utils.langchain.message_builder import build_message_content


def _image_item(object_key: str, name: str = "pic.png") -> ChatFileWithContent:
    return ChatFileWithContent(
        file=ChatFile(
            id=1,
            file_name=name,
            file_ext=".png",
            file_size=1,
            content_type="image/png",
            storage_type="local",
            object_key=object_key,
            upload_user_id=1,
            session_id="s1",
            parse_status=1,
        ),
        content=None,
    )


def test_build_message_content_appends_inline_ref_marker(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    item = _image_item("att/k.png")
    blocks = build_message_content("hi", [item], image_ref_ids={"att/k.png": "3"})

    # text(hi) -> image -> text(marker)
    assert blocks[1]["type"] == "image"
    marker = blocks[-1]
    assert marker["type"] == "text"
    assert "图片 #3" in marker["text"]
    assert "source_image_id=3" in marker["text"]


def test_build_message_content_no_marker_without_ref(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    blocks = build_message_content("hi", [_image_item("att/k.png")])
    assert all("图片 #" not in b.get("text", "") for b in blocks)


def test_annotate_ai_generated_images_internal_only(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    seen = []

    def assign(object_key, label, source):
        seen.append((object_key, source))
        return str(len(seen))

    msg = AIMessage(
        id="a1",
        content=(
            "done ![Generated Image](https://cdn.example.com/g/x.png) "
            "and ![ext](https://other.example.org/y.png)"
        ),
    )
    out = ChatFileService._annotate_ai_generated_images(msg, assign)

    assert "![图片 #1](https://cdn.example.com/g/x.png)" in out.content
    # external url untouched, no id assigned for it
    assert "![ext](https://other.example.org/y.png)" in out.content
    assert seen == [("g/x.png", "generated_image")]


def test_annotate_skips_non_ai_and_textless(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    def assign(*_):
        raise AssertionError("should not assign")

    human = HumanMessage(id="h", content="![x](https://cdn.example.com/g/x.png)")
    assert ChatFileService._annotate_ai_generated_images(human, assign) is human

    plain = AIMessage(id="a", content="no images here")
    assert ChatFileService._annotate_ai_generated_images(plain, assign) is plain


async def _seed_attachment(session, *, message_id: str, object_key: str) -> int:
    f = ChatFile(
        file_name="pic.png",
        file_ext=".png",
        file_size=1,
        content_type="image/png",
        storage_type="local",
        object_key=object_key,
        upload_user_id=1,
        session_id="s1",
        parse_status=1,
    )
    session.add(f)
    await session.flush()
    session.add(ChatMessageFile(message_id=message_id, file_id=f.id))
    await session.commit()
    return f.id


@pytest.mark.asyncio
async def test_inject_numbers_attachment_then_generated(async_session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    await _seed_attachment(async_session, message_id="h1", object_key="att/a.png")

    messages = [
        HumanMessage(id="h1", content="edit my photo"),
        AIMessage(
            id="a1",
            content="here ![Generated Image](https://cdn.example.com/gen/b.png)",
        ),
    ]

    service = ChatFileService(async_session)
    out = await service.inject_files_into_messages(messages, user_id=1)

    # attachment -> #1 marker on the human message
    human_texts = [b.get("text", "") for b in out[0].content if isinstance(b, dict)]
    assert any("图片 #1" in t and "source_image_id=1" in t for t in human_texts)

    # generated image -> #2 alt rewrite on the AI message
    assert "![图片 #2](https://cdn.example.com/gen/b.png)" in out[1].content

    # last human message must NOT carry the old reference table
    assert all("可编辑图片引用表" not in t for t in human_texts)

    # ContextVar holds both, mapped to the right object_key, resolvable by id
    refs = {r.ref_id: r.object_key for r in get_image_references()}
    assert refs == {"1": "att/a.png", "2": "gen/b.png"}
    assert resolve_image_ref_id("image 2").object_key == "gen/b.png"
    assert resolve_image_ref_id("#1").object_key == "att/a.png"


@pytest.mark.asyncio
async def test_inject_pure_text_conversation(async_session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    messages = [
        HumanMessage(id="h1", content="hello"),
        AIMessage(id="a1", content="world, no images here"),
        HumanMessage(id="h2", content="another turn"),
    ]

    service = ChatFileService(async_session)
    out = await service.inject_files_into_messages(messages, user_id=1)

    # messages returned unchanged
    assert len(out) == 3
    assert out[0].content == "hello"
    assert out[1].content == "world, no images here"
    assert out[2].content == "another turn"

    # ref list is empty
    assert get_image_references() == []


@pytest.mark.asyncio
async def test_inject_ids_stable_when_history_grows(async_session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    await _seed_attachment(async_session, message_id="h1", object_key="att/a.png")
    service = ChatFileService(async_session)

    base = [
        HumanMessage(id="h1", content="edit"),
        AIMessage(id="a1", content="![g](https://cdn.example.com/gen/b.png)"),
    ]
    await service.inject_files_into_messages(list(base), user_id=1)
    first = {r.ref_id: r.object_key for r in get_image_references()}

    # a new turn appends another generated image; older ids must not shift
    grown = base + [
        HumanMessage(id="h2", content="again"),
        AIMessage(id="a2", content="![g2](https://cdn.example.com/gen/c.png)"),
    ]
    await service.inject_files_into_messages(grown, user_id=1)
    second = {r.ref_id: r.object_key for r in get_image_references()}

    assert first == {"1": "att/a.png", "2": "gen/b.png"}
    assert second == {"1": "att/a.png", "2": "gen/b.png", "3": "gen/c.png"}
