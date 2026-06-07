from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.api.llm_router import router as llm_router
from app.api.mcp_router import router as mcp_router
from app.api.agent_router import router as agent_router
from app.api.agent_mcp_router import router as agent_mcp_router
from app.api.chat_router import router as chat_router
from app.api.auth_router import router as auth_router
from app.api.upload_router import router as upload_router
from app.api.session_router import router as session_router
from app.api.api_tool_router import router as api_tool_router
from app.api.agent_api_tool_router import router as agent_api_tool_router
from app.api.agent_image_tool_router import router as agent_image_tool_router
from app.api.email_agent_router import router as email_agent_router
from app.api.scheduled_task_router import router as scheduled_task_router
from app.api.image_tool_router import router as image_tool_router
from app.api.generated_image_router import router as generated_image_router
from app.api.stats_router import router as stats_router
from app.api.agent_builtin_tool_router import router as agent_builtin_tool_router, builtin_catalog_router
from app.api.prompt_template_router import router as prompt_template_router
from app.api.skill_router import router as skill_router
from app.api.user_memory_router import router as user_memory_router
from app.api.kg_router import router as kg_router
from app.api.help_document_router import router as help_document_router
from app.api.agent_webhook_router import router as agent_webhook_router
from app.api.webhook_trigger_router import router as webhook_trigger_router
from app.api.telegram_webhook_router import router as telegram_webhook_router
from app.api.dingtalk_webhook_router import router as dingtalk_webhook_router
from app.api.discord_interaction_router import router as discord_interaction_router
from app.api.session_share_router import router as session_share_router
from app.api.workspace_router import router as workspace_router

from app.deps.user import get_current_user
from app.core.logging_config import setup_logging, get_logger
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.database import init_db
from app.middleware.request_logging import RequestLoggingMiddleware

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化日志（使用配置）
    setup_logging(
        log_dir=settings.log_dir,
        app_name=settings.app_name,
        log_level=settings.log_level,
        json_format=settings.log_json_format,
        console_output=settings.log_console_output
    )
    logger = get_logger(__name__)
    logger.info(f"应用启动 - 环境: {settings.app_env}")
    await init_db()

    # 启动时幂等载入 system skills 种子（找不到文件就跳过）
    try:
        import json
        from pathlib import Path
        from app.deps.db import get_db_session
        from app.services.skill_service import SkillService
        seed_path = Path(__file__).parent / "seed" / "system_skills.json"
        if seed_path.exists():
            data = json.loads(seed_path.read_text(encoding="utf-8"))
            async with get_db_session() as db:
                svc = SkillService(db)
                for item in data:
                    await svc.upsert_system_skill(item)
            logger.info(f"载入 {len(data)} 条 system skills")
    except Exception as e:
        logger.warning(f"system skills 种子载入失败: {e}")

    await start_scheduler()

    yield

    # 关闭时清理
    await stop_scheduler()
    logger.info("应用关闭")


# 创建应用
app = FastAPI(
    title="Fancy Agent Backend",
    description="Backend service for Fancy Agent application",
    version="0.1.0",
    lifespan=lifespan
)
app.add_middleware(
    RequestLoggingMiddleware,
    log_request_body=settings.log_request_body,
    skip_paths=settings.log_skip_paths
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(llm_router)
api_router.include_router(mcp_router)
api_router.include_router(agent_router)
api_router.include_router(agent_mcp_router)
api_router.include_router(chat_router)
api_router.include_router(session_router)
api_router.include_router(auth_router)
api_router.include_router(upload_router)
api_router.include_router(api_tool_router)
api_router.include_router(agent_api_tool_router)
api_router.include_router(agent_image_tool_router)
api_router.include_router(email_agent_router)
api_router.include_router(scheduled_task_router)
api_router.include_router(image_tool_router)
api_router.include_router(generated_image_router)
api_router.include_router(stats_router)
api_router.include_router(agent_builtin_tool_router)
api_router.include_router(builtin_catalog_router)
api_router.include_router(prompt_template_router)
api_router.include_router(skill_router)
api_router.include_router(user_memory_router)
api_router.include_router(kg_router)
api_router.include_router(help_document_router)
api_router.include_router(agent_webhook_router)
api_router.include_router(webhook_trigger_router)
api_router.include_router(telegram_webhook_router)
api_router.include_router(dingtalk_webhook_router)
api_router.include_router(discord_interaction_router)
api_router.include_router(session_share_router)
api_router.include_router(workspace_router)

app.include_router(api_router)
@app.get("/protected")
def protected_route(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id, "message": "Access granted"}

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=(settings.app_env == "development"),
        log_config=None  # 禁用 uvicorn 默认日志配置
    )
