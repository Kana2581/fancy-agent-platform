from types import SimpleNamespace
import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.utils.langchain import agent_util
from app.utils.langchain.builtin_tools.bash_exec import BashExecTool
from app.utils.langchain.builtin_tools.sandbox_tool import build_sandbox_tool
from app.services.skill_catalog_service import SkillCatalogEntry
from app.schemas.dto.langchian import ValidChatModel


@pytest.mark.asyncio
async def test_skill_tools_are_not_injected_without_bash(monkeypatch):
    monkeypatch.setattr(agent_util, "init_chat_model", lambda **kwargs: object())
    agent_data = SimpleNamespace(
        llm=ValidChatModel(provider="custom", model_name="test-model"),
        user_id=7,
        mcps=None,
        api_tools=None,
        image_tools=None,
        builtin_tools=[],
        skills=[],
    )

    _, tools = await agent_util._build_model_and_tools(agent_data, skills=[])

    assert {tool.name for tool in tools} == set()


@pytest.mark.asyncio
async def test_legacy_skill_manager_builds_one_unified_sandbox(monkeypatch):
    monkeypatch.setattr(agent_util, "init_chat_model", lambda **kwargs: object())
    agent_data = SimpleNamespace(
        llm=ValidChatModel(provider="custom", model_name="test-model"),
        user_id=7,
        id=1,
        mcps=None,
        api_tools=None,
        image_tools=None,
        builtin_tools=["skill_manager", "python_exec", "workspace_manager"],
    )

    _, tools = await agent_util._build_model_and_tools(agent_data, session_id="session")

    assert [tool.name for tool in tools] == ["sandbox"]


@pytest.mark.asyncio
async def test_skill_prompt_requires_a_runtime_capable_sandbox(monkeypatch):
    skill = SkillCatalogEntry(
        scope="system",
        user_id=None,
        package_path="demo",
        name="demo",
        description="Demo skill",
        status="ready",
        error=None,
        files=(),
    )
    agent_data = SimpleNamespace(
        system_prompt="base",
        user_id=None,
        image_tools=None,
    )

    hidden = await agent_util._build_system_prompt(agent_data, skills=[skill], tools=[])
    visible = await agent_util._build_system_prompt(
        agent_data,
        skills=[skill],
        tools=[SimpleNamespace(name="sandbox", supports_skills=True)],
    )

    assert "可用 Skills" not in hidden
    assert "可用 Skills" in visible
    assert "sandbox(command=...)" in visible
    assert "operation=execute" not in visible


@pytest.mark.asyncio
async def test_sandbox_command_is_not_overwritten_by_langgraph(monkeypatch):
    async def fake_bash(self, command, cwd=None):
        return json.dumps({"runtime": "bash", "command": command, "cwd": cwd})

    monkeypatch.setattr(BashExecTool, "_arun", fake_bash)
    monkeypatch.setattr(FakeMessagesListChatModel, "bind_tools", lambda self, *args, **kwargs: self)
    model = FakeMessagesListChatModel(responses=[
        AIMessage(
            content="",
            tool_calls=[{
                "name": "sandbox",
                "args": {"command": "pwd"},
                "id": "call-sandbox",
            }],
        ),
        AIMessage(content="done"),
    ])
    agent = agent_util.create_langchain_agent_with_middleware(
        model,
        [build_sandbox_tool(user_id=7, session_id="session")],
    )

    result = await agent.ainvoke({"messages": [HumanMessage(content="run")]})
    tool_message = next(message for message in result["messages"] if isinstance(message, ToolMessage))

    assert tool_message.status == "success"
    assert json.loads(tool_message.content)["runtime"] == "bash"


def test_sandbox_schema_and_description_are_bash_only():
    tool = build_sandbox_tool(user_id=7, session_id="session")

    assert set(tool.args_schema.model_fields) == {"command"}
    assert "普通问答" in tool.description
    assert "只允许写入 /workspace 及 /skills/user" in tool.description
    assert "/skills/system 只允许读取" in tool.description
    assert "需要 Python 时在 command 中调用 python" in tool.description
    assert "operation" not in tool.description
    assert "execution_runtime" not in tool.description
    assert tool.args_schema.model_config["extra"] == "forbid"


@pytest.mark.asyncio
async def test_sandbox_rejects_empty_command():
    tool = build_sandbox_tool(user_id=7, session_id="session")

    missing = json.loads(await tool._arun(command=""))
    whitespace = json.loads(await tool._arun(command="   "))

    assert "非空 command" in missing["error"]
    assert "非空 command" in whitespace["error"]
