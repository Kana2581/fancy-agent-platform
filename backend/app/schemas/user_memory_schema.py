from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel


class UserMemoryCreate(BaseModel):
    key: str
    content: str
    memory_type: Literal["core", "normal"] = "normal"
    category: Optional[str] = None


class UserMemoryUpdate(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[Literal["core", "normal"]] = None
    category: Optional[str] = None


class UserMemoryOut(BaseModel):
    id: int
    user_id: int
    key: str
    content: str
    memory_type: str
    category: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
