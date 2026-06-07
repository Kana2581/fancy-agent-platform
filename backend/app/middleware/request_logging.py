"""
Production-grade FastAPI logging middleware
Supports SSE, streaming responses, and WebSocket
ASGI-native implementation (no BaseHTTPMiddleware)
"""

import time
import uuid
import json
import logging
from typing import Callable, Awaitable

from starlette.types import ASGIApp, Scope, Receive, Send, Message

logger = logging.getLogger("api.access")

SENSITIVE_BODY_KEYS = {
    "password",
    "secret",
    "dingtalk_app_secret",
    "token",
    "telegram_bot_token",
    "refresh_token",
    "access_token",
}


def _redact_sensitive_body(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if key.lower() in SENSITIVE_BODY_KEYS or key.lower().endswith("_token"):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = _redact_sensitive_body(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_body(item) for item in value]
    return value


class RequestLoggingMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        max_body_size: int = 4096,
        skip_paths: list[str] | None = None,
    ):
        self.app = app
        self.log_request_body = log_request_body
        self.max_body_size = max_body_size
        self.skip_paths = skip_paths or ["/health", "/metrics"]

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        start_time = time.time()

        path = scope.get("path", "")
        method = scope.get("method", "")
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        headers = {
            k.decode(): v.decode()
            for k, v in scope.get("headers", [])
        }

        user_agent = headers.get("user-agent", "unknown")

        # ---- Skip paths ----
        if path in self.skip_paths:
            await self.app(scope, receive, send)
            return

        # ---- Optional request body capture ----
        body_chunks = []
        body_size = 0

        async def receive_wrapper() -> Message:
            nonlocal body_size

            message = await receive()

            if (
                self.log_request_body
                and scope["type"] == "http"
                and message["type"] == "http.request"
            ):
                chunk = message.get("body", b"")

                if chunk and body_size < self.max_body_size:
                    remaining = self.max_body_size - body_size
                    body_chunks.append(chunk[:remaining])
                    body_size += len(chunk[:remaining])

            return message

        # ---- Log request start ----
        logger.info(
            "request_started",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "ip": client_ip,
                "user_agent": user_agent,
            },
        )

        status_code = None

        # ---- Send wrapper to capture response metadata ----
        async def send_wrapper(message: Message):
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

                # Inject request ID header
                headers = message.setdefault("headers", [])
                headers.append(
                    (b"x-request-id", request_id.encode())
                )

            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)

            duration_ms = int((time.time() - start_time) * 1000)

            request_body = None
            if body_chunks:
                try:
                    raw = b"".join(body_chunks).decode("utf-8", errors="ignore")
                    request_body = json.loads(raw) if raw.startswith("{") else raw
                    request_body = _redact_sensitive_body(request_body)
                except Exception:
                    request_body = "<unparseable>"

            log_data = {
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "ip": client_ip,
            }

            if request_body is not None:
                log_data["request_body"] = request_body

            level = logging.INFO if (status_code or 500) < 400 else logging.WARNING

            logger.log(level, "request_completed", extra=log_data)

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)

            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "ip": client_ip,
                },
            )

            raise
