import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.api.discord_interaction_router import (
    _conversation_scope,
    _extract_command_content,
    _verify_discord_signature,
)


def test_verify_discord_signature_accepts_valid_request():
    private_key = Ed25519PrivateKey.generate()
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    timestamp = "1700000000"
    body = json.dumps({"type": 1}, separators=(",", ":")).encode("utf-8")
    signature_hex = private_key.sign(timestamp.encode("utf-8") + body).hex()

    assert _verify_discord_signature(public_key_hex, timestamp, signature_hex, body)
    assert not _verify_discord_signature(public_key_hex, timestamp, signature_hex, b"{}")


def test_extract_command_content_prefers_prompt_option():
    interaction = {
        "data": {
            "name": "ask",
            "options": [
                {"name": "mode", "type": 3, "value": "fast"},
                {"name": "prompt", "type": 3, "value": "帮我总结一下"},
            ],
        }
    }

    assert _extract_command_content(interaction) == "帮我总结一下"


def test_extract_command_content_handles_subcommand_options():
    interaction = {
        "data": {
            "name": "agent",
            "options": [
                {
                    "name": "ask",
                    "type": 1,
                    "options": [
                        {"name": "question", "type": 3, "value": "部署怎么做？"},
                    ],
                }
            ],
        }
    }

    assert _extract_command_content(interaction) == "部署怎么做？"


def test_conversation_scope_isolated_by_user_within_same_channel():
    alice_interaction = {
        "guild_id": "guild-1",
        "channel_id": "channel-1",
        "member": {"user": {"id": "user-alice"}},
    }
    bob_interaction = {
        "guild_id": "guild-1",
        "channel_id": "channel-1",
        "member": {"user": {"id": "user-bob"}},
    }

    assert _conversation_scope(alice_interaction) == ("channel-1", "user-alice")
    assert _conversation_scope(bob_interaction) == ("channel-1", "user-bob")


def _build_discord_client(monkeypatch):
    """构造仅挂载 Discord 路由的应用，并 patch 掉签名校验与 DB 查询。"""
    from types import SimpleNamespace

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.api.discord_interaction_router as router_module

    fake_webhook = SimpleNamespace(
        id=1,
        name="t",
        channel="discord",
        enabled=True,
        discord_public_key="00" * 32,
    )

    async def fake_get_by_slug(self, slug):  # noqa: ANN001
        return fake_webhook

    monkeypatch.setattr(router_module.AgentWebhookMapper, "get_by_slug", fake_get_by_slug)
    monkeypatch.setattr(router_module, "_verify_discord_signature", lambda *a, **k: True)

    application = FastAPI()
    application.include_router(router_module.router, prefix="/api/v1")
    return TestClient(application)


def test_ping_interaction_returns_pong(monkeypatch):
    client = _build_discord_client(monkeypatch)
    resp = client.post(
        "/api/v1/discord/interactions/test-slug",
        content=json.dumps({"type": 1}),
        headers={"x-signature-timestamp": "1", "x-signature-ed25519": "ab"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"type": 1}


def test_unsupported_interaction_type_returns_ephemeral(monkeypatch):
    client = _build_discord_client(monkeypatch)
    resp = client.post(
        "/api/v1/discord/interactions/test-slug",
        content=json.dumps({"type": 99}),
        headers={"x-signature-timestamp": "1", "x-signature-ed25519": "ab"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == 4
    assert body["data"]["flags"] == 64


def test_application_command_returns_deferred_and_schedules_task(monkeypatch):
    import app.api.discord_interaction_router as router_module

    scheduled = {}
    original_create_task = router_module.asyncio.create_task

    async def fake_run_and_reply(*args, **kwargs):  # noqa: ANN002, ANN003
        scheduled["run_called"] = True

    def fake_create_task(coro):
        scheduled["called"] = True
        return original_create_task(coro)

    monkeypatch.setattr(router_module, "_run_and_reply", fake_run_and_reply)
    monkeypatch.setattr(router_module.asyncio, "create_task", fake_create_task)

    client = _build_discord_client(monkeypatch)
    resp = client.post(
        "/api/v1/discord/interactions/test-slug",
        content=json.dumps(
            {
                "type": 2,
                "data": {"name": "ask", "options": [{"name": "prompt", "type": 3, "value": "hi"}]},
            }
        ),
        headers={"x-signature-timestamp": "1", "x-signature-ed25519": "ab"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"type": 5}
    assert scheduled.get("called") is True
