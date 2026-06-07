from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class SessionShareCreate(BaseModel):
    expires_in_hours: Optional[int] = None  # None = 永不过期


class SessionShareOut(BaseModel):
    id: int
    session_id: str
    slug: str
    enabled: bool
    expires_at: Optional[datetime]
    view_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SharedMessage(BaseModel):
    id: str
    type: str
    content: Any  # 文本 / 结构化（图片等）；tool 类型已脱敏
    name: Optional[str] = None
    created_at: datetime


class SharedSessionView(BaseModel):
    slug: str
    session_title: Optional[str]
    agent_avatar: Optional[str]
    agent_description: Optional[str]
    messages: List[SharedMessage]
    created_at: datetime
    expires_at: Optional[datetime]
