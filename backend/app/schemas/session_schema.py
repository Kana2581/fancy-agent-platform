from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class SessionBase(BaseModel):

    agent_id: int
    title: Optional[str] = None
    is_active: bool = True


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None


class SessionOut(SessionBase):
    id: str
    user_id: int
    auto_title_generated: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class SessionPageOut(BaseModel):
    items: List[SessionOut]
    total: int
