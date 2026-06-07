# app/schemas/llm_schema.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class LLMCreate(BaseModel):

    provider: str
    model_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class LLMUpdate(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class LLMTestRequest(BaseModel):
    provider: str
    model_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    llm_id: Optional[int] = None


class LLMTestResult(BaseModel):
    success: bool
    message: str


class LLMOut(BaseModel):
    id: int
    user_id: int
    provider: str
    model_name: str
    base_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {
        "from_attributes": True
    }
