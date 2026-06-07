
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatFileUploadRequest(BaseModel):
    session_id: Optional[int] = None   # 可选，上传时绑定会话


class ChatFileResponse(BaseModel):
    id: int
    file_name: str
    file_ext: str
    file_size: int
    content_type: Optional[str]
    storage_type: str
    url: str                           # 由 object_key 转换，不存库
    md5: Optional[str]
    parse_status: int
    created_at: datetime

    model_config = {"from_attributes": True}