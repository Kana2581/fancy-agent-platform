
from dataclasses import dataclass
from typing import Optional

from app.models.chat_file import ChatFile
from app.models.chat_file_content import ChatFileContent


@dataclass(slots=True)
class ChatFileWithContent:
    """文件 + 解析内容 DTO（用于上层拼装消息）"""
    file: ChatFile
    content: Optional[ChatFileContent]