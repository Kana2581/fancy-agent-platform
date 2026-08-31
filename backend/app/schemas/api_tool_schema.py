import re
from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class TemplateVariable(BaseModel):
    name: str
    type: Literal["string", "integer", "number", "boolean"]
    description: str = ""
    required: bool = True
    default: Any = None


class ApiToolBase(BaseModel):
    name: str
    description: Optional[str] = None
    url: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    param_location: Literal["query", "body", "path_and_query", "path_and_body"] = "query"
    request_template: Any = Field(default_factory=dict)
    tool_params: List[TemplateVariable] = Field(default_factory=list)
    response_template: Optional[str] = None
    response_max_chars: int = 2000

    @field_validator("name")
    @classmethod
    def name_must_be_ascii(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("工具名只能包含英文字母、数字、下划线和连字符，不支持中文或特殊字符")
        if len(v) > 64:
            raise ValueError("工具名不能超过 64 个字符")
        return v


class ApiToolCreate(ApiToolBase):
    pass


class ApiToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    method: Optional[Literal["GET", "POST", "PUT", "DELETE", "PATCH"]] = None
    headers: Optional[dict[str, str]] = None
    param_location: Optional[Literal["query", "body", "path_and_query", "path_and_body"]] = None
    request_template: Optional[Any] = None
    tool_params: Optional[List[TemplateVariable]] = None
    response_template: Optional[str] = None
    response_max_chars: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_must_be_ascii(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError("工具名只能包含英文字母、数字、下划线和连字符，不支持中文或特殊字符")
            if len(v) > 64:
                raise ValueError("工具名不能超过 64 个字符")
        return v


class ApiToolOut(ApiToolBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
