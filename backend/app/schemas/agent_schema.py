
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.schemas.llm_schema import LLMOut
from app.schemas.mcp_schema import MCPOut
from pydantic import Field

class AgentBase(BaseModel):

    avatar: Optional[str]
    model_id: int
    description: Optional[str]
    system_prompt: Optional[str]
    max_token_size: Optional[int]
    human_in_the_loop: Optional[bool]=Field(default=False)

class AgentCreate(AgentBase):
    mcp_ids: Optional[List[int]] = None


class AgentUpdate(AgentBase):
    mcp_ids: Optional[List[int]] = None
    pass

class AgentOut(AgentBase):
    user_id: int
    id: int
    created_at: datetime
    updated_at: datetime
    mcp_ids: Optional[List[int]]=None
    model_config = {
        "from_attributes": True
    }
class AgentMCPOut(MCPOut):
    has_mcp: bool
class AgentFullOut(AgentOut):
    llm:Optional[LLMOut]=None
    mcps:Optional[List[AgentMCPOut]]=None
