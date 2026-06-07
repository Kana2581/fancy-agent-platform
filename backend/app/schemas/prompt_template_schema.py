from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class PromptTemplateCreate(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    category: Optional[str] = None


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class PromptTemplateOut(BaseModel):
    id: int
    user_id: int
    name: str
    content: str
    description: Optional[str]
    category: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {
        "from_attributes": True
    }
