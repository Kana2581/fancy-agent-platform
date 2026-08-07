import pytest
from jsonschema import Draft202012Validator
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from app.schemas.structured_output_schema import StructuredOutputFieldConfig
from app.utils.langchain.agent_util import create_langchain_agent_with_middleware
from app.utils.langchain.message_processor import MessageProcessor
from app.utils.structured_output import compile_json_schema
from app.services.chat_service import ChatService


FIELD_CONFIG = {
    "fields": [
        {
            "key": "contract_no",
            "label": "合同编号",
            "type": "string",
            "description": "合同中的编号",
        },
        {
            "key": "amount",
            "label": "金额",
            "type": "number",
        },
        {
            "key": "currency",
            "label": "币种",
            "type": "enum",
            "enum_values": ["CNY", "USD"],
        },
    ]
}


def test_compile_json_schema_requires_nullable_fields_and_forbids_extras():
    schema = compile_json_schema(FIELD_CONFIG, name="合同提取")

    assert schema["required"] == ["contract_no", "amount", "currency"]
    assert schema["additionalProperties"] is False
    validator = Draft202012Validator(schema)
    assert not list(validator.iter_errors({"contract_no": None, "amount": 12.5, "currency": "CNY"}))
    assert list(validator.iter_errors({"contract_no": "X", "amount": 12.5}))
    assert list(
        validator.iter_errors(
            {"contract_no": "X", "amount": 12.5, "currency": "EUR", "extra": True}
        )
    )


def test_compile_json_schema_supports_object_arrays():
    schema = compile_json_schema(
        {
            "fields": [
                {
                    "key": "contacts",
                    "label": "联系人",
                    "type": "object_array",
                    "description": "文本中出现的所有联系人及地址",
                    "item_fields": [
                        {"key": "name", "label": "姓名", "type": "string"},
                        {"key": "phone", "label": "电话", "type": "string"},
                        {"key": "address", "label": "地址", "type": "string"},
                        {
                            "key": "role",
                            "label": "角色",
                            "type": "enum",
                            "enum_values": ["客户", "收件人", "紧急联系人"],
                        },
                    ],
                }
            ]
        },
        name="联系人提取",
    )

    contacts_schema = schema["properties"]["contacts"]["anyOf"][0]
    assert contacts_schema["type"] == "array"
    assert contacts_schema["items"]["required"] == ["name", "phone", "address", "role"]
    assert contacts_schema["items"]["additionalProperties"] is False

    validator = Draft202012Validator(schema)
    assert not list(
        validator.iter_errors(
            {
                "contacts": [
                    {
                        "name": "张明远",
                        "phone": "138-0000-1234",
                        "address": "北京市朝阳区望京街道花园路88号锦绣家园3号楼2单元1502室",
                        "role": "客户",
                    },
                    {
                        "name": "李晓雯",
                        "phone": None,
                        "address": "上海市浦东新区世纪大道168号海景国际中心B座1208室",
                        "role": "收件人",
                    },
                ]
            }
        )
    )
    assert list(
        validator.iter_errors(
            {
                "contacts": [
                    {
                        "name": "王建国",
                        "address": "广东省深圳市南山区科技园南区科苑路36号创新大厦7层",
                        "role": "紧急联系人",
                    }
                ]
            }
        )
    )


@pytest.mark.parametrize(
    "field_config",
    [
        {"fields": []},
        {"fields": [{"key": "bad-key", "label": "Bad", "type": "string"}]},
        {
            "fields": [
                {"key": "same", "label": "A", "type": "string"},
                {"key": "same", "label": "B", "type": "integer"},
            ]
        },
        {"fields": [{"key": "status", "label": "状态", "type": "enum"}]},
        {"fields": [{"key": "contacts", "label": "联系人", "type": "object_array"}]},
        {
            "fields": [
                {
                    "key": "groups",
                    "label": "分组",
                    "type": "object_array",
                    "item_fields": [
                        {"key": "children", "label": "子项", "type": "object_array"}
                    ],
                }
            ]
        },
    ],
)
def test_invalid_field_configs_are_rejected(field_config):
    with pytest.raises(ValidationError):
        StructuredOutputFieldConfig.model_validate(field_config)


def test_agent_builder_forwards_response_format(monkeypatch):
    captured = {}

    def fake_create_agent(*args, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.utils.langchain.agent_util.create_agent", fake_create_agent)
    response_format = ProviderStrategy(compile_json_schema(FIELD_CONFIG, name="合同提取"))
    create_langchain_agent_with_middleware(
        model=object(),
        tools=[],
        response_format=response_format,
    )

    assert captured["response_format"] is response_format


def test_message_processor_persists_structured_artifact():
    message = AIMessage(id="ai-1", content='{"contract_no":"X"}')
    artifact = {
        "type": "structured_output",
        "schema_id": 1,
        "schema_snapshot": FIELD_CONFIG,
        "data": {"contract_no": "X"},
        "status": "valid",
    }
    processor = MessageProcessor(session_id="s-1", user_id=1)
    processor.add(message, artifact=artifact)

    orm_message = processor.to_orm()[0]
    assert orm_message.content == '{"contract_no":"X"}'
    assert orm_message.artifact == artifact


@pytest.mark.asyncio
async def test_chat_service_attaches_artifact_to_provider_ai_message(monkeypatch):
    class FakeAgent:
        async def astream(self, **_kwargs):
            ai = AIMessage(
                id="ai-structured",
                content='{"contract_no":"X"}',
            )
            yield "updates", {
                "model": {
                    "messages": [ai],
                    "structured_response": {"contract_no": "X"},
                }
            }

    persisted = []

    async def fake_persist(processor):
        persisted.extend(processor.to_orm())

    monkeypatch.setattr(ChatService, "_persist", staticmethod(fake_persist))
    streamed = []
    async for message, _parent in ChatService().chat(
        "session-1",
        1,
        FakeAgent(),
        [],
        "human-1",
        structured_output_context={
            "schema_id": 1,
            "schema_name": "合同",
            "schema_snapshot": FIELD_CONFIG,
        },
    ):
        streamed.append(message)

    assert [message.id for message in streamed] == ["ai-structured"]
    assert len(persisted) == 1
    assert persisted[0].type == "ai"
    assert persisted[0].artifact["data"] == {"contract_no": "X"}
