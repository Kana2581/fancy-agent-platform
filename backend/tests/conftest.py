import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base


@pytest.fixture(autouse=True)
def _force_local_storage(monkeypatch):
    """Pin storage to the local backend for every test.

    The developer's `.env` may set STORAGE_BACKEND=s3; without this, tests that go
    through the storage factory would route writes to a real bucket (and break
    local-disk assertions). Storage-specific tests monkeypatch this back to 's3'.
    """
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local", raising=False)

# Register all models with Base.metadata so every table exists when create_all runs.
# This matters when running a single test file in isolation.
from app.models.agent import Agent  # noqa: F401
from app.models.agent_api_tool import AgentApiTool  # noqa: F401
from app.models.agent_builtin_tool import AgentBuiltinTool  # noqa: F401
from app.models.agent_image_tool import AgentImageTool  # noqa: F401
from app.models.agent_mcp import AgentMCP  # noqa: F401
from app.models.agent_webhook import AgentWebhook  # noqa: F401
from app.models.api_tool import ApiTool  # noqa: F401
from app.models.chat_file import ChatFile  # noqa: F401
from app.models.chat_message import ChatMessage  # noqa: F401
from app.models.image_tool import ImageTool  # noqa: F401
from app.models.llm import LLM  # noqa: F401
from app.models.mcp import MCP  # noqa: F401
from app.models.scheduled_task import ScheduledTask  # noqa: F401
from app.models.scheduled_task_execution import ScheduledTaskExecution  # noqa: F401
from app.models.telegram_conversation import TelegramConversation  # noqa: F401
from app.models.user import User  # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Mirror the PRAGMA from database.py so FK constraints fire in tests too.
    @event.listens_for(engine.sync_engine, "connect")
    def _fk_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
        await session.rollback()
