from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db

from app.services.agent_service import AgentService
from app.services.chat_file_service import ChatFileService
from app.services.chat_message_service import ChatMessageService
from app.services.session_service import SessionService
from app.services.mcp_service import MCPService

from app.services.llm_service import LLMService
from app.services.agent_api_tool_service import AgentApiToolService
from app.services.agent_image_tool_service import AgentImageToolService
from app.services.agent_mcp_service import AgentMCPService
from app.services.api_tool_service import ApiToolService
from app.services.chat_service import ChatService
from app.services.user_service import UserService


def get_mcp_service(db: AsyncSession = Depends(get_db)) -> MCPService:
    return MCPService(db=db)

def get_agent_service(db: AsyncSession = Depends(get_db)) -> AgentService:
    return AgentService(db=db)

def get_agent_mcp_service(db: AsyncSession = Depends(get_db)) -> AgentMCPService:
    return AgentMCPService(db=db)

def get_chat_message_service(db: AsyncSession = Depends(get_db)) -> ChatMessageService:
    return ChatMessageService(db=db)

def get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db=db)

def get_llm_service(db: AsyncSession = Depends(get_db)) -> LLMService:
    return LLMService(db=db)

def get_chat_service() -> ChatService:
    return ChatService()

def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db=db)

def get_chat_file_service(db: AsyncSession = Depends(get_db)) -> ChatFileService:
    return ChatFileService(db=db)

def get_api_tool_service(db: AsyncSession = Depends(get_db)) -> ApiToolService:
    return ApiToolService(db=db)

def get_agent_api_tool_service(db: AsyncSession = Depends(get_db)) -> AgentApiToolService:
    return AgentApiToolService(db=db)

def get_agent_image_tool_service(db: AsyncSession = Depends(get_db)) -> AgentImageToolService:
    return AgentImageToolService(db=db)

from app.services.image_tool_service import ImageToolService
from app.services.generated_image_service import GeneratedImageService
from app.services.stats_service import StatsService


def get_image_tool_service(db: AsyncSession = Depends(get_db)) -> ImageToolService:
    return ImageToolService(db=db)


def get_generated_image_service(db: AsyncSession = Depends(get_db)) -> GeneratedImageService:
    return GeneratedImageService(db=db)


def get_stats_service(db: AsyncSession = Depends(get_db)) -> StatsService:
    return StatsService(db=db)


from app.services.agent_builtin_tool_service import AgentBuiltinToolService


def get_agent_builtin_tool_service(db: AsyncSession = Depends(get_db)) -> AgentBuiltinToolService:
    return AgentBuiltinToolService(db=db)


from app.services.prompt_template_service import PromptTemplateService


def get_prompt_template_service(db: AsyncSession = Depends(get_db)) -> PromptTemplateService:
    return PromptTemplateService(db=db)


from app.services.skill_service import SkillService


def get_skill_service(db: AsyncSession = Depends(get_db)) -> SkillService:
    return SkillService(db=db)


from app.services.user_memory_service import UserMemoryService


def get_user_memory_service(db: AsyncSession = Depends(get_db)) -> UserMemoryService:
    return UserMemoryService(db=db)


from app.services.kg_service import KGService


def get_kg_service(db: AsyncSession = Depends(get_db)) -> KGService:
    return KGService(db=db)


from app.services.help_document_service import HelpDocumentService


def get_help_document_service(db: AsyncSession = Depends(get_db)) -> HelpDocumentService:
    return HelpDocumentService(db=db)


from app.services.agent_webhook_service import AgentWebhookService


def get_agent_webhook_service(db: AsyncSession = Depends(get_db)) -> AgentWebhookService:
    return AgentWebhookService(db=db)
