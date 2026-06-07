
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class MCPCreate(BaseModel):
    mcp_name: str
    transport: str
    config_json: Optional[dict] = None
    is_builtin: Optional[bool] = False
    is_enabled: Optional[bool] = True

class MCPUpdate(BaseModel):
    mcp_name: Optional[str] = None
    transport: Optional[str] = None
    config_json: Optional[dict] = None
    is_enabled: Optional[bool] = None

class MCPOut(BaseModel):
    id: int
    user_id: Optional[int]
    mcp_name: str
    transport: str
    config_json: Optional[dict]
    is_builtin: bool
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


    model_config = {
        "from_attributes": True
    }
