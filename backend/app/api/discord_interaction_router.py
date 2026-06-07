import asyncio
from typing import Any

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, HTTPException, Request

from app.core.logging_config import get_logger
from app.deps.db import get_db_session
from app.mappers.agent_webhook_mapper import AgentWebhookMapper
from app.services.agent_webhook_service import record_trigger
from app.services.webhook_agent_runner import run_agent_webhook_message

logger = get_logger(__name__)

router = APIRouter(prefix="/discord/interactions", tags=["DiscordInteractions"])

DISCORD_API_BASE = "https://discord.com/api/v10"
INTERACTION_PING = 1
INTERACTION_APPLICATION_COMMAND = 2
CALLBACK_PONG = 1
CALLBACK_DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
CALLBACK_CHANNEL_MESSAGE_WITH_SOURCE = 4
MAX_DISCORD_CONTENT_LENGTH = 2000

# asyncio 只持有 task 的弱引用，必须保留强引用，否则后台回复任务可能被 GC 中途回收
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _verify_discord_signature(
    public_key_hex: str,
    timestamp: str,
    signature_hex: str,
    body: bytes,
) -> bool:
    if not public_key_hex or not timestamp or not signature_hex:
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex.strip()))
        signature = bytes.fromhex(signature_hex.strip())
    except ValueError:
        return False

    try:
        public_key.verify(signature, timestamp.encode("utf-8") + body)
    except InvalidSignature:
        return False
    return True


def _iter_options(options: list[dict[str, Any]] | None):
    for option in options or []:
        nested = option.get("options")
        if isinstance(nested, list):
            yield from _iter_options(nested)
        yield option


def _extract_command_content(interaction: dict[str, Any]) -> str | None:
    raw_data = interaction.get("data")
    data = raw_data if isinstance(raw_data, dict) else {}
    preferred_names = {"prompt", "content", "message", "text", "question"}
    string_values: list[str] = []

    for option in _iter_options(data.get("options")):
        value = option.get("value")
        if isinstance(value, str) and value.strip():
            if str(option.get("name", "")).lower() in preferred_names:
                return value.strip()
            string_values.append(value.strip())

    if string_values:
        return string_values[0]
    return None


def _conversation_scope(interaction: dict[str, Any]) -> tuple[str, str]:
    channel_id = str(interaction.get("channel_id") or "")
    guild_id = str(interaction.get("guild_id") or "")
    member = interaction.get("member")
    user = member.get("user") if isinstance(member, dict) else None
    if not isinstance(user, dict):
        raw_user = interaction.get("user")
        user = raw_user if isinstance(raw_user, dict) else {}
    user_id = str(user.get("id") or "")
    # Discord slash commands should keep per-user context isolation even inside the
    # same guild/channel, otherwise different members can accidentally share history.
    primary = channel_id or guild_id or user_id or str(interaction.get("id") or "")
    secondary = user_id or guild_id or "discord"
    return primary, secondary


def _response_content(text: str) -> str:
    fallback = "Agent 没有返回文本内容。"
    content = text or fallback
    if len(content) <= MAX_DISCORD_CONTENT_LENGTH:
        return content
    suffix = "\n\n[回复过长，已截断]"
    return content[: MAX_DISCORD_CONTENT_LENGTH - len(suffix)] + suffix


async def _edit_original_interaction_response(
    application_id: str,
    interaction_token: str,
    content: str,
) -> None:
    url = (
        f"{DISCORD_API_BASE}/webhooks/{application_id}/"
        f"{interaction_token}/messages/@original"
    )
    payload = {
        "content": _response_content(content),
        "allowed_mentions": {"parse": []},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.patch(url, json=payload)
        response.raise_for_status()


async def _run_and_reply(slug: str, webhook, interaction: dict[str, Any], content: str) -> None:
    application_id = str(interaction.get("application_id") or "")
    interaction_token = str(interaction.get("token") or "")
    # 触发计数：仅统计真正进入 Agent 执行的请求（与 Telegram/DingTalk 语义一致，不依赖执行成败）
    await record_trigger(webhook.id)
    try:
        _session_id, _last_ai_id, reply = await run_agent_webhook_message(
            webhook=webhook,
            content=content,
            session_title=f"Discord: {webhook.name}",
            conversation_scope=_conversation_scope(interaction),
        )
        await _edit_original_interaction_response(application_id, interaction_token, reply)
    except Exception as exc:
        logger.exception(f"Discord interaction agent failed for slug {slug}: {exc}")
        if application_id and interaction_token:
            try:
                await _edit_original_interaction_response(
                    application_id,
                    interaction_token,
                    "Agent 执行失败，请稍后再试。",
                )
            except Exception as reply_exc:
                logger.exception(f"Discord error reply failed for slug {slug}: {reply_exc}")


@router.post("/{slug}")
async def trigger_discord_interaction(slug: str, request: Request):
    raw_body = await request.body()

    async with get_db_session() as db:
        webhook = await AgentWebhookMapper(db).get_by_slug(slug)

    if not webhook or webhook.channel != "discord":
        raise HTTPException(status_code=404, detail="Discord interaction webhook not found")
    if not webhook.enabled:
        raise HTTPException(status_code=403, detail="Discord interaction webhook disabled")
    if not webhook.discord_public_key:
        raise HTTPException(status_code=500, detail="Discord public key is not configured")

    timestamp = request.headers.get("x-signature-timestamp", "")
    signature = request.headers.get("x-signature-ed25519", "")
    if not _verify_discord_signature(webhook.discord_public_key, timestamp, signature, raw_body):
        raise HTTPException(status_code=401, detail="Invalid Discord signature")

    try:
        interaction = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Discord interaction: {exc}")

    interaction_type = interaction.get("type")
    if interaction_type == INTERACTION_PING:
        return {"type": CALLBACK_PONG}
    if interaction_type != INTERACTION_APPLICATION_COMMAND:
        return {
            "type": CALLBACK_CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "content": "暂不支持这种 Discord 交互类型。",
                "flags": 64,
                "allowed_mentions": {"parse": []},
            },
        }

    content = _extract_command_content(interaction)
    if not content:
        return {
            "type": CALLBACK_CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "content": "请在 Slash Command 的文本参数里输入要发送给 Agent 的内容。",
                "flags": 64,
                "allowed_mentions": {"parse": []},
            },
        }

    task = asyncio.create_task(_run_and_reply(slug, webhook, interaction, content))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return {"type": CALLBACK_DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE}
