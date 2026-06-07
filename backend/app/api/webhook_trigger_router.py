import hmac
import hashlib
import re

from fastapi import APIRouter, HTTPException, Request

from app.core.logging_config import get_logger
from app.deps.db import get_db_session
from app.mappers.agent_webhook_mapper import AgentWebhookMapper
from app.schemas.agent_webhook_schema import WebhookTriggerRequest, WebhookTriggerResponse
from app.services.agent_webhook_service import record_trigger
from app.services.webhook_agent_runner import run_agent_webhook_message

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["WebhookTrigger"])

UTF8_BOM = b"\xef\xbb\xbf"


def _normalize_signature(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("sha256="):
        normalized = normalized[len("sha256="):]
    return re.sub(r"[\s:-]", "", normalized).lower()


def _verify_signature(secret: str, body_bytes: bytes, header_value: str) -> bool:
    if not header_value:
        return False
    received = _normalize_signature(header_value)
    expected = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    if len(received) != len(expected):
        return False
    return hmac.compare_digest(expected, received)


@router.post("/{slug}", response_model=WebhookTriggerResponse)
async def trigger_webhook(slug: str, request: Request):
    raw_body = await request.body()

    async with get_db_session() as db:
        webhook = await AgentWebhookMapper(db).get_by_slug(slug)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if not webhook.enabled:
        raise HTTPException(status_code=403, detail="Webhook disabled")
    if webhook.channel != "generic":
        raise HTTPException(status_code=404, detail="Webhook not found")

    signature_header = request.headers.get("x-signature", "") or request.headers.get(
        "x-hub-signature-256", ""
    )
    if not _verify_signature(webhook.secret, raw_body, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload_body = raw_body.removeprefix(UTF8_BOM)
    try:
        payload = WebhookTriggerRequest.model_validate_json(payload_body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    try:
        session_id, last_ai_id, content = await run_agent_webhook_message(
            webhook=webhook,
            content=payload.content,
            session_title=f"Webhook: {webhook.name}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Webhook trigger failed for slug {slug}: {exc}")
        raise HTTPException(status_code=500, detail="Agent execution failed")

    await record_trigger(webhook.id)
    return WebhookTriggerResponse(
        session_id=session_id,
        message_id=last_ai_id,
        content=content,
    )
