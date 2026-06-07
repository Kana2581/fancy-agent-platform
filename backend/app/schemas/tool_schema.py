from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
class ToolParameters(BaseModel):
    type: Literal["object"] = "object"
    properties: Dict[str, Any]
    required: Optional[List[str]] = None
class ToolOut(BaseModel):
    name: str
    description: str
    parameters: ToolParameters
class ToolOutList(BaseModel):
    tools: List[ToolOut]
