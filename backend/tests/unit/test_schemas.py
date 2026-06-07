import pytest

from app.schemas.dto.langchian import ValidAgent, ValidChatModel, ValidMCP
from app.schemas.agent_webhook_schema import AgentWebhookCreate


class TestValidChatModel:
    def test_alias_mapping(self):
        model = ValidChatModel.model_validate({"provider": "openai", "model_name": "gpt-4o"})
        assert model.model_provider == "openai"
        assert model.model == "gpt-4o"

    def test_provider_normalization_custom(self):
        model = ValidChatModel.model_validate({"provider": "Custom", "model_name": "x"})
        assert model.model_provider == "openai"

    def test_provider_normalization_aliyun(self):
        model = ValidChatModel.model_validate({"provider": "aliyun", "model_name": "qwen-max"})
        assert model.model_provider == "openai"

    def test_provider_normalization_google(self):
        model = ValidChatModel.model_validate({"provider": "google", "model_name": "gemini-pro"})
        assert model.model_provider == "google_genai"

    def test_provider_normalization_azure(self):
        model = ValidChatModel.model_validate({"provider": "azure", "model_name": "gpt-4"})
        assert model.model_provider == "azure_openai"

    def test_empty_base_url_becomes_none(self):
        model = ValidChatModel.model_validate({
            "provider": "openai",
            "model_name": "gpt-4",
            "base_url": "",
            "api_key": "",
        })
        assert model.base_url is None
        assert model.api_key is None

    def test_unknown_provider_kept_as_lowercase(self):
        model = ValidChatModel.model_validate({"provider": "MYVENDOR", "model_name": "v1"})
        assert model.model_provider == "myvendor"

    def test_model_config_allows_field_name(self):
        model = ValidChatModel(model_provider="openai", model="gpt-4o")
        assert model.model == "gpt-4o"


class TestValidAgentMcpFilter:
    _BASE = {
        "id": 1,
        "user_id": 1,
        "avatar": None,
        "model_id": 1,
        "description": None,
        "system_prompt": None,
        "max_token_size": 4096,
        "human_in_the_loop": False,
    }

    def _mcp(self, id_: int, has_mcp: bool) -> dict:
        return {
            "id": id_,
            "user_id": 1,
            "mcp_name": f"mcp_{id_}",
            "transport": "stdio",
            "config_json": {},
            "has_mcp": has_mcp,
        }

    def test_invalid_mcps_filtered_out(self):
        data = {**self._BASE, "mcps": [self._mcp(1, True), self._mcp(2, False)]}
        agent = ValidAgent.model_validate(data)
        assert len(agent.mcps) == 1
        assert agent.mcps[0].id == 1

    def test_all_valid_mcps_kept(self):
        data = {**self._BASE, "mcps": [self._mcp(1, True), self._mcp(2, True)]}
        agent = ValidAgent.model_validate(data)
        assert len(agent.mcps) == 2

    def test_all_invalid_mcps_returns_empty(self):
        data = {**self._BASE, "mcps": [self._mcp(1, False), self._mcp(2, False)]}
        agent = ValidAgent.model_validate(data)
        assert agent.mcps == []

    def test_none_mcps_unchanged(self):
        agent = ValidAgent.model_validate({**self._BASE, "mcps": None})
        assert agent.mcps is None

    def test_human_in_the_loop_defaults_false(self):
        agent = ValidAgent.model_validate({**self._BASE, "human_in_the_loop": False})
        assert agent.human_in_the_loop is False


class TestAgentWebhookCreate:
    def test_dingtalk_requires_app_secret(self):
        with pytest.raises(ValueError):
            AgentWebhookCreate(agent_id=1, name="dt", channel="dingtalk")

    def test_dingtalk_accepts_app_secret(self):
        data = AgentWebhookCreate(
            agent_id=1,
            name="dt",
            channel="dingtalk",
            dingtalk_app_secret="secret",
        )
        assert data.channel == "dingtalk"
