import time

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import app.api.dingtalk_webhook_router as router_module
from app.api.dingtalk_webhook_router import (
    _build_verification_response,
    _expected_signature,
    _extract_message,
    _get_dingtalk_signature_parts,
    _verify_dingtalk_signature,
)


def test_dingtalk_signature_accepts_decoded_sign():
    # FastAPI auto-decodes query params, so _verify_dingtalk_signature receives
    # the raw base64 string (not URL-encoded).
    timestamp = str(int(time.time() * 1000))
    secret = "test-secret"
    sign = _expected_signature(timestamp, secret)

    assert _verify_dingtalk_signature(secret, timestamp, sign)


def test_dingtalk_signature_rejects_stale_timestamp():
    timestamp = str(int((time.time() - 7200) * 1000))
    secret = "test-secret"
    sign = _expected_signature(timestamp, secret)

    assert not _verify_dingtalk_signature(secret, timestamp, sign)


def test_get_dingtalk_signature_parts_prefers_headers():
    app = FastAPI()

    @app.post("/test")
    async def route(request: Request):
        return dict(zip(("timestamp", "sign"), _get_dingtalk_signature_parts(request)))

    client = TestClient(app)
    resp = client.post(
        "/test?timestamp=query-ts&sign=query-sign",
        headers={"x-dingtalk-timestamp": "header-ts", "x-dingtalk-sign": "header-sign"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"timestamp": "header-ts", "sign": "header-sign"}


def test_build_verification_response_returns_challenge():
    app = FastAPI()

    @app.post("/test")
    async def route(request: Request):
        return {
            "body_challenge": _build_verification_response({"challenge": "abc123"}, request),
            "empty_body_challenge": _build_verification_response({"challenge": ""}, request),
        }

    client = TestClient(app)
    resp = client.post("/test")

    assert resp.status_code == 200
    assert resp.json()["body_challenge"] == {"challenge": "abc123"}
    assert resp.json()["empty_body_challenge"] is None


def test_extract_dingtalk_text_message():
    conversation_id, sender_id, content, title = _extract_message(
        {
            "conversationId": "cid-1",
            "senderStaffId": "user-1",
            "conversationTitle": "研发群",
            "conversationType": "2",
            "isInAtList": True,
            "msgtype": "text",
            "text": {"content": "  帮我总结今天的告警  "},
        }
    )

    assert conversation_id == "cid-1"
    assert sender_id == "user-1"
    assert content == "帮我总结今天的告警"
    assert title == "研发群"


def test_extract_dingtalk_group_message_ignores_when_not_at_bot():
    _conversation_id, _sender_id, content, _title = _extract_message(
        {
            "conversationId": "cid-1",
            "conversationType": "2",
            "isInAtList": False,
            "msgtype": "text",
            "text": {"content": "不该触发"},
        }
    )

    assert content is None


def test_trigger_dingtalk_webhook_returns_challenge_during_verification(monkeypatch):
    from types import SimpleNamespace

    async def fake_get_by_slug(self, slug):  # noqa: ANN001
        return SimpleNamespace(
            id=1,
            name="dt",
            channel="dingtalk",
            enabled=True,
            dingtalk_app_secret="secret",
        )

    monkeypatch.setattr(router_module.AgentWebhookMapper, "get_by_slug", fake_get_by_slug)
    monkeypatch.setattr(router_module, "_verify_dingtalk_signature", lambda *a, **k: True)

    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1")
    client = TestClient(app)

    resp = client.post(
        "/api/v1/dingtalk/webhooks/test-slug",
        json={"challenge": "verify-me"},
        headers={"x-dingtalk-timestamp": "1", "x-dingtalk-sign": "ok"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"challenge": "verify-me"}


def test_extract_dingtalk_group_message_ignores_when_is_in_at_list_absent():
    # isInAtList 字段缺失时也应被过滤（None 等同于 False）
    _conversation_id, _sender_id, content, _title = _extract_message(
        {
            "conversationId": "cid-1",
            "conversationType": "2",
            "msgtype": "text",
            "text": {"content": "不该触发"},
        }
    )

    assert content is None
