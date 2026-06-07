from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class UserEmailAgentCreate(BaseModel):
    agent_id: int


class UserEmailAgentUpdate(BaseModel):
    agent_id: Optional[int] = None
    is_enabled: Optional[bool] = None


class UserEmailAgentOut(BaseModel):
    id: int
    user_id: int
    agent_id: int
    session_id: Optional[str] = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
