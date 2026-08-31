import httpx
import pytest

from app.utils.langchain import http_tool_factory


class FakeResponse:
    text = '{"ok":true}'

    def json(self):
        return {
            "data": {
                "city": "上海",
                "temperature": 26,
                "items": [{"name": "one"}, {"name": "two"}],
            }
        }

    def raise_for_status(self):
        return None


class FakeClient:
    last_request = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, method, url, **kwargs):
        self.last_request = (method, url, kwargs)
        FakeClient.last_request = self.last_request
        return FakeResponse()


def config(**overrides):
    value = {
        "name": "weather_lookup",
        "description": "weather",
        "url": "https://example.test/weather/{{city}}",
        "method": "POST",
        "headers": {"Authorization": "Bearer {{token}}"},
        "param_location": "path_and_body",
        "request_template": {"page": "{{page}}", "verbose": "{{verbose}}", "label": "for {{city}}"},
        "tool_params": [
            {"name": "city", "type": "string", "required": True},
            {"name": "token", "type": "string", "required": True},
            {"name": "page", "type": "integer", "required": True},
            {"name": "verbose", "type": "boolean", "required": True},
        ],
        "response_template": "{{data.city}}: {{data.items[*]}}",
        "response_max_chars": 2000,
    }
    value.update(overrides)
    return value


def test_extract_variables_is_unique_and_ordered():
    assert http_tool_factory.extract_template_variables(
        "/{{city}}", {"Authorization": "{{token}}"}, {"again": "{{city}}"}
    ) == ["city", "token"]


def test_template_tool_renders_url_headers_body_and_response(monkeypatch):
    monkeypatch.setattr(http_tool_factory.httpx, "Client", FakeClient)
    tool = http_tool_factory.build_tool_from_config(config())

    result = tool.invoke({"city": "上海/浦东", "token": "secret", "page": 2, "verbose": True})

    method, url, request = FakeClient.last_request
    assert method == "POST"
    assert url.endswith("%E4%B8%8A%E6%B5%B7%2F%E6%B5%A6%E4%B8%9C")
    assert request["headers"] == {"Authorization": "Bearer secret"}
    assert request["json"] == {"page": 2, "verbose": True, "label": "for 上海/浦东"}
    assert result.startswith("上海:")
    assert '"name": "one"' in result


def test_template_tool_renders_header_names(monkeypatch):
    monkeypatch.setattr(http_tool_factory.httpx, "Client", FakeClient)
    tool = http_tool_factory.build_tool_from_config(
        config(
            headers={"X-{{tenant}}-Token": "Bearer {{token}}"},
            tool_params=config()["tool_params"] + [
                {"name": "tenant", "type": "string", "required": True}
            ],
        )
    )

    tool.invoke({"city": "上海", "tenant": "acme", "token": "secret", "page": 2, "verbose": True})

    assert FakeClient.last_request[2]["headers"] == {"X-acme-Token": "Bearer secret"}


def test_missing_template_variable_is_rejected_before_request(monkeypatch):
    monkeypatch.setattr(http_tool_factory.httpx, "Client", FakeClient)
    FakeClient.last_request = None
    tool = http_tool_factory.build_tool_from_config(config())

    with pytest.raises((ValueError, TypeError)):
        tool.invoke({"city": "上海", "token": "secret", "page": 2})
    assert FakeClient.last_request is None


def test_undeclared_template_variable_is_rejected():
    with pytest.raises(ValueError, match="模板变量未声明"):
        http_tool_factory.build_tool_from_config(config(tool_params=[]))


def test_invalid_template_variable_is_rejected():
    with pytest.raises(ValueError, match="非法模板变量"):
        http_tool_factory.build_tool_from_config(config(url="https://example.test/{{city-name}}"))


def test_http_error_is_propagated(monkeypatch):
    class ErrorResponse(FakeResponse):
        def raise_for_status(self):
            raise httpx.HTTPStatusError("bad gateway", request=None, response=None)

    class ErrorClient(FakeClient):
        def request(self, method, url, **kwargs):
            return ErrorResponse()

    monkeypatch.setattr(http_tool_factory.httpx, "Client", ErrorClient)
    tool = http_tool_factory.build_tool_from_config(config())
    with pytest.raises(httpx.HTTPStatusError):
        tool.invoke({"city": "上海", "token": "secret", "page": 2, "verbose": True})
