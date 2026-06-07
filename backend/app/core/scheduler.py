from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def _purge_expired_refresh_tokens():
    from app.deps.db import get_db_session
    from app.services.token_service import purge_expired_tokens
    try:
        async with get_db_session() as db:
            await purge_expired_tokens(db)
        logger.info("过期 Refresh Token 清理完成")
    except Exception as e:
        logger.error(f"过期 Refresh Token 清理失败: {e}", exc_info=True)

_scheduler: AsyncIOScheduler | None = None


async def start_scheduler():
    global _scheduler

    _scheduler = AsyncIOScheduler()

    # Email polling job (only when email is enabled)
    if settings.EMAIL_ENABLED:
        from app.services.email_polling_service import EmailPollingService
        polling_service = EmailPollingService()
        _scheduler.add_job(
            polling_service.poll,
            trigger="interval",
            seconds=settings.EMAIL_CHECK_INTERVAL,
            id="email_polling",
            replace_existing=True,
        )
        logger.info(f"邮件轮询调度器已配置，间隔 {settings.EMAIL_CHECK_INTERVAL} 秒")
    else:
        logger.info("邮件服务未启用，跳过邮件轮询 Job")

    # Scheduled task checker (always enabled)
    from app.services.scheduled_task_service import execute_due_tasks
    check_interval = settings.SCHEDULED_TASK_CHECK_INTERVAL
    _scheduler.add_job(
        execute_due_tasks,
        trigger="interval",
        seconds=check_interval,
        id="scheduled_task_checker",
        replace_existing=True,
    )
    logger.info(f"定时任务检查器已配置，间隔 {check_interval} 秒")

    # Refresh token cleanup (runs once every 24 hours)
    _scheduler.add_job(
        _purge_expired_refresh_tokens,
        trigger="interval",
        seconds=86400,
        id="refresh_token_purge",
        replace_existing=True,
    )
    logger.info("过期 Refresh Token 清理任务已配置，间隔 24 小时")

    _scheduler.start()
    logger.info("调度器已启动")


async def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("调度器已停止")


# Keep old names as aliases for backward compatibility
start_email_polling = start_scheduler
stop_email_polling = stop_scheduler
