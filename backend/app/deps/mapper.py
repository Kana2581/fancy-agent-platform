from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db
from app.mappers.agent_mapper import AgentMapper
from app.mappers.agent_mcp_mapper import AgentMCPMapper
from app.mappers.chat_message_mapper import ChatMessageMapper
from app.mappers.llm_mapper import LLMMapper
from app.mappers.mcp_mapper import MCPMapper
from app.mappers.session_mapper import SessionMapper


def get_agent_mapper(db:AsyncSession=Depends(get_db)):
    return AgentMapper(db=db)

def get_agent_mcp_mapper(db:AsyncSession=Depends(get_db)):
    return AgentMCPMapper(db=db)

def chat_message_mapper(db:AsyncSession=Depends(get_db)):
    return ChatMessageMapper(db=db)

def get_llm_mapper(db:AsyncSession=Depends(get_db)):
    return LLMMapper(db=db)

def get_mcp_mapper(db:AsyncSession=Depends(get_db)):
    return MCPMapper(db=db)

def get_session_mapper(db:AsyncSession=Depends(get_db)):
    return SessionMapper(db=db)

def get_chat_message_mapper(db:AsyncSession=Depends(get_db)):
    return ChatMessageMapper(db=db)


