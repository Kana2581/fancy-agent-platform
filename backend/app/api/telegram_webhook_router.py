import hmac
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.core.logging_config import get_logger
from app.deps.db import get_db_session
from app.mappers.agent_webhook_mapper import AgentWebhookMapper
from app.services.agent_webhook_service import record_trigger
from app.services.webhook_agent_runner import run_agent_webhook_message

logger = get_logger(__name__)

router = APIRouter(prefix="/telegram/webhooks", tags=["TelegramWebhooks"])


def _extract_message(update: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return None, None, None

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return None, None, None

    text = message.get("text") or message.get("caption")
    if not text:
        return str(chat_id), str(message.get("message_thread_id") or ""), None

    return str(chat_id), str(message.get("message_thread_id") or ""), str(text)


async def _send_telegram_message(
    bot_token: str, chat_id: str, text: str, message_thread_id: str = ""
) -> None:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text or "Agent 没有返回文本内容。",
        "disable_web_page_preview": True,
    }
    if message_thread_id:
        payload["message_thread_id"] = int(message_thread_id)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
        )
        response.raise_for_status()


@router.post("/{slug}")
async def trigger_telegram_webhook(slug: str, request: Request):
    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Telegram update: {exc}")

    async with get_db_session() as db:
        webhook = await AgentWebhookMapper(db).get_by_slug(slug)

    if not webhook or webhook.channel != "telegram":
        raise HTTPException(status_code=404, detail="Telegram webhook not found")
    if not webhook.enabled:
        raise HTTPException(status_code=403, detail="Telegram webhook disabled")

    secret_token = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not hmac.compare_digest(secret_token, webhook.secret):
        raise HTTPException(status_code=401, detail="Invalid Telegram secret token")
    if not webhook.telegram_bot_token:
        raise HTTPException(status_code=500, detail="Telegram bot token is not configured")

    chat_id, message_thread_id, content = _extract_message(update)
    if not chat_id or not content:
        return {"ok": True, "ignored": True}

    try:
        _session_id, _last_ai_id, reply = await run_agent_webhook_message(
            webhook=webhook,
            content=content,
            session_title=f"Telegram: {webhook.name} ({chat_id})",
            conversation_scope=(chat_id, message_thread_id or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Telegram webhook agent failed for slug {slug}: {exc}")
        raise HTTPException(status_code=500, detail="Agent execution failed")

    try:
        await _send_telegram_message(
            webhook.telegram_bot_token, chat_id, reply, message_thread_id or ""
        )
    except httpx.HTTPError as exc:
        logger.exception(f"Telegram sendMessage failed for slug {slug}: {exc}")
        raise HTTPException(status_code=502, detail="Telegram sendMessage failed")

    await record_trigger(webhook.id)
    return {"ok": True}
