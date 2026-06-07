# app/utils/message_builder.py

import base64
import logging
from typing import Dict, List, Optional, Union

from langchain_core.messages.content import ImageContentBlock, TextContentBlock

from app.core.config import settings
from app.schemas.dto.file_message import ChatFileWithContent
from app.utils.image.local_image_loader import mime_from_ext, read_local_image

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def extract_text(content: Union[str, List[TextContentBlock | ImageContentBlock]]) -> str:
    """从 LangChain content 中提取纯文本"""
    if isinstance(content, str):
        return content

    texts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            texts.append(item.get("text", ""))

    return "\n".join(texts)


def _build_image_block(object_key: str, file_ext: str) -> ImageContentBlock:
    """
    构造 ImageContentBlock：
    - 优先读本地文件转 base64，避免依赖公网 URL
    - 本地读失败兜底回落为 url 形式（保持旧行为，便于排查）
    """
    try:
        data, mime = read_local_image(object_key)
        b64 = base64.b64encode(data).decode("ascii")
        return ImageContentBlock(type="image", base64=b64, mime_type=mime)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning(
            "image base64 fallback to url for object_key=%s: %s",
            object_key,
            exc,
        )
        url = f"{settings.OSS_URL.rstrip('/')}/{object_key.lstrip('/')}"
        return ImageContentBlock(
            type="image",
            url=url,
            mime_type=mime_from_ext(file_ext),
        )


def build_message_content(
    original_text: str,
    files: List[ChatFileWithContent],
    image_ref_ids: Optional[Dict[str, str]] = None,
) -> List[TextContentBlock | ImageContentBlock]:
    """
    构造新的多模态 content：
    - 原始文本
    - 文件内容注入
    - 图片走 base64 inline，不再依赖公网 OSS_URL
    - 文件内容超过 5000 字符自动截断

    `image_ref_ids`：可选的 object_key -> 图片编号 映射。命中时在该图片块之后
    紧跟一个文本标记（「图片 #N」），让模型就地知道这张图的可编辑 id，
    取代以往把整张引用表追加到最后一条消息的做法。
    """

    image_ref_ids = image_ref_ids or {}
    content: List[TextContentBlock | ImageContentBlock] = []

    if original_text:
        content.append(TextContentBlock(type="text", text=original_text))

    for item in files:
        file = item.file
        file_content = item.content

        if file.file_ext.lower() in IMAGE_EXTENSIONS:
            content.append(_build_image_block(file.object_key, file.file_ext))
            ref_id = image_ref_ids.get(file.object_key)
            if ref_id:
                content.append(TextContentBlock(
                    type="text",
                    text=f"（图片 #{ref_id}，编辑此图请传 source_image_id={ref_id}）",
                ))
        elif file_content and file_content.content:
            text = file_content.content

            if file_content.content_length and file_content.content_length > 5000:
                text = text[:5000] + "\n\n..."

            content.append(TextContentBlock(
                type="text",
                text=f"\n\n【文件：{file.file_name}】\n{text}",
            ))

    return content
