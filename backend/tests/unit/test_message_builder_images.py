"""Coverage for the base64-inline image pipeline in message_builder.

The LLM message path must not depend on a publicly fetchable OSS_URL anymore
— images that exist locally are encoded directly as base64 blocks.
"""

import base64
from io import BytesIO

import pytest
from PIL import Image

from app.core.config import settings
from app.models.chat_file import ChatFile
from app.schemas.dto.file_message import ChatFileWithContent
from app.utils.langchain.message_builder import build_message_content


def _write_png(path):
    img = Image.new("RGB", (4, 4), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    path.write_bytes(buf.getvalue())
    return buf.getvalue()


def _make_image_file(object_key: str) -> ChatFileWithContent:
    chat_file = ChatFile(
        id=1,
        file_name="pic.png",
        file_ext=".png",
        file_size=123,
        content_type="image/png",
        storage_type="local",
        object_key=object_key,
        upload_user_id=1,
        session_id="s1",
        parse_status=1,
    )
    return ChatFileWithContent(file=chat_file, content=None)


def test_build_message_content_uses_base64_when_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    img_dir = tmp_path / "2026" / "05" / "25"
    img_dir.mkdir(parents=True)
    img_path = img_dir / "abc.png"
    raw = _write_png(img_path)

    item = _make_image_file("2026/05/25/abc.png")
    blocks = build_message_content("look at this", [item])

    assert blocks[0]["type"] == "text"
    image_block = blocks[1]
    assert image_block["type"] == "image"
    assert image_block["mime_type"] == "image/png"
    assert "base64" in image_block
    assert "url" not in image_block
    assert base64.b64decode(image_block["base64"]) == raw


def test_build_message_content_falls_back_to_url_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    item = _make_image_file("does/not/exist.png")
    blocks = build_message_content("", [item])

    assert len(blocks) == 1
    image_block = blocks[0]
    assert image_block["type"] == "image"
    assert image_block["url"] == "https://cdn.example.com/does/not/exist.png"
    assert "base64" not in image_block


@pytest.mark.asyncio
async def test_load_image_bytes_prefers_local_for_internal_oss_url(tmp_path, monkeypatch):
    from app.utils.image.local_image_loader import load_image_bytes

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OSS_URL", "https://cdn.example.com")

    img_path = tmp_path / "gen" / "x.png"
    img_path.parent.mkdir(parents=True)
    raw = _write_png(img_path)

    data, mime = await load_image_bytes(image_url="https://cdn.example.com/gen/x.png")
    assert data == raw
    assert mime == "image/png"


@pytest.mark.asyncio
async def test_load_image_bytes_rejects_path_traversal(tmp_path, monkeypatch):
    from app.utils.image.local_image_loader import load_image_bytes

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    with pytest.raises(ValueError):
        await load_image_bytes(object_key="../escape.png")
