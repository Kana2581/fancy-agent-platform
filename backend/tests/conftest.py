import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.deps.db import get_db
from app.main import app


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


@pytest_asyncio.fixture
async def test_app(async_engine):
    factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    yield app
    del app.dependency_overrides[get_db]


@pytest_asyncio.fixture
async def api_client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def create_user_and_login(api_client):
    counter = 0

    async def _create_user_and_login(
        *,
        username: str | None = None,
        email: str | None = None,
        password: str = "secret123",
    ) -> tuple[dict, dict[str, str]]:
        nonlocal counter
        counter += 1
        username = username or f"user{counter}"
        email = email or f"user{counter}@example.com"

        register_response = await api_client.post(
            "/api/v1/auth/register",
            json={"email": email, "username": username, "password": password},
        )
        assert register_response.status_code == 200, register_response.text

        login_response = await api_client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]
        return register_response.json(), {"Authorization": f"Bearer {token}"}

    return _create_user_and_login

