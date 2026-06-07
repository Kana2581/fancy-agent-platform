from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class SkillFileIn(BaseModel):
    path: str
    content: str


class SkillFileOut(BaseModel):
    path: str
    content: str
    size: int
    model_config = {"from_attributes": True}


class SkillCreate(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    category: Optional[str] = None
    scope: Optional[str] = None  # system/user/session；默认 user
    session_id: Optional[str] = None
    files: Optional[List[SkillFileIn]] = None


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    files: Optional[List[SkillFileIn]] = None


class SkillOut(BaseModel):
    id: int
    user_id: int
    name: str
    content: str
    description: Optional[str]
    category: Optional[str]
    scope: Optional[str] = "user"
    session_id: Optional[str] = None
    files: List[SkillFileOut] = []
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
