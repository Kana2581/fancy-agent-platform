# app/schemas/llm_schema.py
from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel


class LLMCreate(BaseModel):

    provider: str
    model_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_mode: Literal["chat_completions", "responses"] = "chat_completions"


class LLMUpdate(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_mode: Optional[Literal["chat_completions", "responses"]] = None


class LLMTestRequest(BaseModel):
    provider: str
    model_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    llm_id: Optional[int] = None
    api_mode: Literal["chat_completions", "responses"] = "chat_completions"


class LLMTestResult(BaseModel):
    success: bool
    message: str


class LLMOut(BaseModel):
    id: int
    user_id: int
    provider: str
    model_name: str
    base_url: Optional[str]
    api_mode: Literal["chat_completions", "responses"] = "chat_completions"
    created_at: datetime
    updated_at: datetime
    model_config = {
        "from_attributes": True
    }
