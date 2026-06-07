import base64
import hashlib
import hmac
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.core.logging_config import get_logger
from app.deps.db import get_db_session
from app.mappers.agent_webhook_mapper import AgentWebhookMapper
from app.services.agent_webhook_service import record_trigger
from app.services.webhook_agent_runner import run_agent_webhook_message

logger = get_logger(__name__)

router = APIRouter(prefix="/dingtalk/webhooks", tags=["DingTalkWebhooks"])

_MAX_TIMESTAMP_SKEW_MS = 60 * 60 * 1000


def _expected_signature(timestamp: str, app_secret: str) -> str:
    string_to_sign = f"{timestamp}\n{app_secret}".encode("utf-8")
    digest = hmac.new(
        app_secret.encode("utf-8"),
        string_to_sign,
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _verify_dingtalk_signature(app_secret: str, timestamp: str, sign: str) -> bool:
    if not app_secret or not timestamp or not sign:
        return False
    try:
        timestamp_ms = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time() * 1000) - timestamp_ms) > _MAX_TIMESTAMP_SKEW_MS:
        return False

    received = sign.strip()
    expected = _expected_signature(timestamp, app_secret)
    return hmac.compare_digest(expected, received)


def _get_dingtalk_signature_parts(request: Request) -> tuple[str, str]:
    timestamp = (
        request.headers.get("x-dingtalk-timestamp")
        or request.headers.get("timestamp")
        or request.query_params.get("timestamp", "")
    )
    sign = (
        request.headers.get("x-dingtalk-sign")
        or request.headers.get("sign")
        or request.query_params.get("sign", "")
    )
    return timestamp, sign


def _build_verification_response(update: dict[str, Any], request: Request) -> dict[str, str] | None:
    challenge = update.get("challenge") or request.query_params.get("challenge")
    if isinstance(challenge, str) and challenge:
        return {"challenge": challenge}
    return None


def _mask_value(value: str, keep: int = 8) -> str:
    if not value:
        return "<empty>"
    if len(value) <= keep:
        return value
    return f"{value[:keep]}..."


def _extract_message(update: dict[str, Any]) -> tuple[str | None, str | None, str | None, str | None]:
    msgtype = update.get("msgtype")
    text = update.get("text") if isinstance(update.get("text"), dict) else {}
    content = text.get("content") if msgtype == "text" else update.get("content")
    if not content:
        return None, None, None, None

    conversation_id = update.get("conversationId") or update.get("conversation_id")
    sender_id = (
        update.get("senderStaffId")
        or update.get("senderId")
        or update.get("senderNick")
        or ""
    )
    if not conversation_id:
        return None, None, None, None

    conversation_type = str(update.get("conversationType") or "")
    is_group_chat = conversation_type == "2"
    is_at_bot = update.get("isInAtList")
    if is_group_chat and not is_at_bot:
        return str(conversation_id), str(sender_id), None, None

    title = update.get("conversationTitle") or update.get("senderNick") or str(conversation_id)
    return str(conversation_id), str(sender_id), str(content).strip(), str(title)


async def _send_dingtalk_message(session_webhook: str, text: str) -> None:
    payload = {
        "msgtype": "text",
        "text": {
            "content": text or "Agent 没有返回文本内容。",
        },
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(session_webhook, json=payload)
        response.raise_for_status()


@router.api_route("/{slug}", methods=["GET", "POST", "HEAD"])
async def trigger_dingtalk_webhook(slug: str, request: Request):
    async with get_db_session() as db:
        webhook = await AgentWebhookMapper(db).get_by_slug(slug)

    if not webhook or webhook.channel != "dingtalk":
        raise HTTPException(status_code=404, detail="DingTalk webhook not found")
    if not webhook.enabled:
        raise HTTPException(status_code=403, detail="DingTalk webhook disabled")
    if not webhook.dingtalk_app_secret:
        raise HTTPException(status_code=500, detail="DingTalk app secret is not configured")

    timestamp, sign = _get_dingtalk_signature_parts(request)
    if request.method in {"GET", "HEAD"} and not timestamp and not sign:
        return {"success": True, "message": "DingTalk webhook endpoint is reachable"}
    if not _verify_dingtalk_signature(webhook.dingtalk_app_secret, timestamp, sign):
        expected_sign = _expected_signature(timestamp, webhook.dingtalk_app_secret) if timestamp else ""
        logger.warning(
            "DingTalk signature verification failed for slug %s: "
            "method=%s header_ts=%s query_ts=%s header_sign=%s query_sign=%s "
            "chosen_ts=%s chosen_sign=%s expected_sign=%s challenge_in_body=%s challenge_in_query=%s",
            slug,
            request.method,
            _mask_value(request.headers.get("x-dingtalk-timestamp") or request.headers.get("timestamp") or ""),
            _mask_value(request.query_params.get("timestamp", "")),
            _mask_value(request.headers.get("x-dingtalk-sign") or request.headers.get("sign") or ""),
            _mask_value(request.query_params.get("sign", "")),
            _mask_value(timestamp),
            _mask_value(sign),
            _mask_value(expected_sign),
            False,
            bool(request.query_params.get("challenge")),
        )
        raise HTTPException(status_code=401, detail="Invalid DingTalk signature")

    update: dict[str, Any] = {}
    if request.method == "POST":
        try:
            update = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid DingTalk update: {exc}")
    if update:
        logger.info(
            "DingTalk webhook payload summary for slug %s: keys=%s challenge_in_body=%s",
            slug,
            sorted(update.keys()),
            isinstance(update.get("challenge"), str) and bool(update.get("challenge")),
        )

    verification_response = _build_verification_response(update, request)
    if verification_response is not None:
        return verification_response

    conversation_id, _sender_id, content, title = _extract_message(update)
    session_webhook = update.get("sessionWebhook")
    session_webhook_expired_at_ms: int | None = update.get("sessionWebhookExpiredTime")
    if not conversation_id or not content:
        return {"success": True, "ignored": True}
    if not session_webhook:
        raise HTTPException(status_code=400, detail="Missing DingTalk sessionWebhook")
    if session_webhook_expired_at_ms and int(time.time() * 1000) > int(session_webhook_expired_at_ms):
        logger.warning(f"DingTalk sessionWebhook already expired on arrival for slug {slug}")
        return {"success": True, "ignored": True}

    try:
        _session_id, _last_ai_id, reply = await run_agent_webhook_message(
            webhook=webhook,
            content=content,
            session_title=f"DingTalk: {webhook.name} ({title or conversation_id})",
            conversation_scope=(conversation_id, ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception(f"DingTalk webhook agent failed for slug {slug}: {exc}")
        raise HTTPException(status_code=500, detail="Agent execution failed")

    if session_webhook_expired_at_ms and int(time.time() * 1000) > int(session_webhook_expired_at_ms):
        logger.warning(f"DingTalk sessionWebhook expired after agent run for slug {slug}, reply dropped")
        await record_trigger(webhook.id)
        return {"success": True}

    try:
        await _send_dingtalk_message(session_webhook, reply)
    except httpx.HTTPError as exc:
        logger.exception(f"DingTalk sessionWebhook send failed for slug {slug}: {exc}")
        raise HTTPException(status_code=502, detail="DingTalk send message failed")

    await record_trigger(webhook.id)
    return {"success": True}
