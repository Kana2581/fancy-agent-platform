# app/db/engine.py
from sqlalchemy import event
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

Base = declarative_base()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine: AsyncEngine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # SQLite doesn't enforce FK constraints by default; enable per connection
    # so ON DELETE CASCADE actually fires (e.g. delete_graph → nodes/edges).
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_fk_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    engine: AsyncEngine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=False,
        future=True,
    )

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # ⭐ 非常重要
    autoflush=False,
)

async def init_db():
    async with engine.begin() as conn:
        # 导入所有模型以确保它们注册到 metadata
        from app.models.llm import LLM  # noqa: F401
        from app.models.image_tool import ImageTool  # noqa: F401
        from app.models.generated_image import GeneratedImage  # noqa: F401
        from app.models.message_approval import MessageApproval  # noqa: F401
        from app.models.agent_image_tool import AgentImageTool  # noqa: F401
        from app.models.agent_builtin_tool import AgentBuiltinTool  # noqa: F401
        from app.models.skill import Skill  # noqa: F401
        from app.models.skill_file import SkillFile  # noqa: F401
        from app.models.user_memory import UserMemory  # noqa: F401
        from app.models.help_document import HelpDocument  # noqa: F401
        from app.models.kg_graph import KGGraph  # noqa: F401
        from app.models.kg_node import KGNode  # noqa: F401
        from app.models.kg_edge import KGEdge  # noqa: F401
        from app.models.agent_webhook import AgentWebhook  # noqa: F401
        from app.models.telegram_conversation import TelegramConversation  # noqa: F401
        from app.models.session_share import SessionShare  # noqa: F401
        from app.models.refresh_token import RefreshToken  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_runtime_schema(conn)


async def _ensure_runtime_schema(conn):
    def has_session_auto_title_generated(sync_conn) -> bool:
        columns = inspect(sync_conn).get_columns("sessions")
        return any(column["name"] == "auto_title_generated" for column in columns)

    if not await conn.run_sync(has_session_auto_title_generated):
        default_value = "0" if _is_sqlite else "FALSE"
        await conn.execute(text(
            "ALTER TABLE sessions "
            f"ADD COLUMN auto_title_generated BOOLEAN NOT NULL DEFAULT {default_value}"
        ))

    def agent_webhooks_columns(sync_conn) -> set[str]:
        return {column["name"] for column in inspect(sync_conn).get_columns("agent_webhooks")}

    webhook_columns = await conn.run_sync(agent_webhooks_columns)
    if "channel" not in webhook_columns:
        await conn.execute(text(
            "ALTER TABLE agent_webhooks "
            "ADD COLUMN channel VARCHAR(24) NOT NULL DEFAULT 'generic'"
        ))
    if "telegram_bot_token" not in webhook_columns:
        await conn.execute(text(
            "ALTER TABLE agent_webhooks "
            "ADD COLUMN telegram_bot_token VARCHAR(128) NULL"
        ))
    if "dingtalk_app_secret" not in webhook_columns:
        await conn.execute(text(
            "ALTER TABLE agent_webhooks "
            "ADD COLUMN dingtalk_app_secret VARCHAR(256) NULL"
        ))
    if "discord_public_key" not in webhook_columns:
        await conn.execute(text(
            "ALTER TABLE agent_webhooks "
            "ADD COLUMN discord_public_key VARCHAR(128) NULL"
        ))
    if "persistent_session_id" not in webhook_columns:
        await conn.execute(text(
            "ALTER TABLE agent_webhooks "
            "ADD COLUMN persistent_session_id VARCHAR(64) NULL"
        ))

    # 敏感字段加密后密文比明文长，MySQL 下把 api_key 列加宽到 TEXT。
    # SQLite 无类型约束，String 列直接存密文即可，无需处理。
    if not _is_sqlite:
        def api_key_col_type(sync_conn, table: str):
            for column in inspect(sync_conn).get_columns(table):
                if column["name"] == "api_key":
                    return str(column["type"]).upper()
            return None

        llm_api_key_type = await conn.run_sync(api_key_col_type, "llms")
        if llm_api_key_type is not None and "TEXT" not in llm_api_key_type:
            await conn.execute(text("ALTER TABLE llms MODIFY api_key TEXT NULL"))

        image_api_key_type = await conn.run_sync(api_key_col_type, "image_tools")
        if image_api_key_type is not None and "TEXT" not in image_api_key_type:
            await conn.execute(text("ALTER TABLE image_tools MODIFY api_key TEXT NOT NULL"))
