from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator


class AgentWebhookCreate(BaseModel):
    agent_id: int
    name: str
    channel: str = "generic"
    telegram_bot_token: Optional[str] = None
    dingtalk_app_secret: Optional[str] = None
    discord_public_key: Optional[str] = None

    @model_validator(mode="after")
    def validate_channel_config(self):
        if self.channel not in {"generic", "telegram", "dingtalk", "discord"}:
            raise ValueError("channel must be generic, telegram, dingtalk, or discord")
        if self.channel == "telegram" and not self.telegram_bot_token:
            raise ValueError("telegram_bot_token is required for Telegram webhooks")
        if self.channel == "dingtalk" and not self.dingtalk_app_secret:
            raise ValueError("dingtalk_app_secret is required for DingTalk webhooks")
        if self.channel == "discord" and not self.discord_public_key:
            raise ValueError("discord_public_key is required for Discord interactions")
        return self


class AgentWebhookUpdate(BaseModel):
    name: Optional[str] = None
    agent_id: Optional[int] = None
    enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    dingtalk_app_secret: Optional[str] = None
    discord_public_key: Optional[str] = None


class AgentWebhookOut(BaseModel):
    """List/detail view — 不含 secret。"""
    id: int
    user_id: int
    agent_id: int
    name: str
    slug: str
    channel: str
    discord_public_key: Optional[str] = None
    enabled: bool
    last_triggered_at: Optional[datetime]
    trigger_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentWebhookOutWithSecret(AgentWebhookOut):
    """仅在创建/重置时返回一次，让用户复制保存。"""
    secret: str


class WebhookTriggerRequest(BaseModel):
    content: str
    metadata: Optional[dict] = None

    @model_validator(mode="before")
    @classmethod
    def accept_common_content_keys(cls, data):
        if isinstance(data, dict) and "content" not in data:
            for key in ("message", "text", "prompt"):
                if key in data:
                    return {**data, "content": data[key]}
        return data


class WebhookTriggerResponse(BaseModel):
    session_id: str
    message_id: Optional[str]
    content: str
