from pydantic import BaseModel
from typing import List


class TokenSummary(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_messages: int
    total_sessions: int


class AgentTokenStat(BaseModel):
    agent_id: int
    agent_name: str
    input_tokens: int
    output_tokens: int
    message_count: int


class DailyTokenStat(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int


class AgentTokenStatList(BaseModel):
    items: List[AgentTokenStat]


class DailyTokenStatList(BaseModel):
    items: List[DailyTokenStat]
