"""Compare structured-output strategies, including a switch back to plain chat.

Usage (PowerShell):
    $env:DEEPEXI_API_KEY = '...'
    uv run python scripts/demo_structured_tool_strategy.py --strategy provider
    uv run python scripts/demo_structured_tool_strategy.py --strategy tool

The API key is intentionally read from the environment and never printed.
"""

from __future__ import annotations

import asyncio
import argparse
import json
import os
from typing import Literal

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy, ToolStrategy
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field


BASE_URL = os.getenv("DEEPEXI_BASE_URL", "https://dts.deepexi.com/v1")
MODEL_NAME = os.getenv("DEEPEXI_MODEL", "gpt-5.5")


@tool
def get_weather(city: str) -> str:
    """获取指定城市当前天气。合同解析流程必须先调用此工具。"""
    # Deterministic fixture: this demo tests the agent loop, not a weather API.
    weather = {
        "Singapore": "晴，31°C，湿度 75%",
        "上海": "多云，28°C，湿度 68%",
    }
    return weather.get(city, f"{city}：天气数据暂不可用")


class ContractResult(BaseModel):
    """The final user-facing contract extraction schema."""

    model_config = ConfigDict(extra="forbid")

    contract_no: str | None = Field(
        description="合同正文中明确标注的合同编号；找不到时为 null"
    )
    seller: str | None = Field(
        description="合同卖方或乙方名称；找不到时为 null"
    )
    buyer: str | None = Field(
        description="合同买方或甲方名称；找不到时为 null"
    )
    total_amount: float | None = Field(
        description="合同含税总金额，只返回数字；找不到时为 null"
    )
    currency: Literal["CNY", "USD", "EUR"] | None = Field(
        description="合同金额币种；找不到时为 null"
    )
    weather_observation: str = Field(
        description="必须原样填写天气工具返回的天气观察结果"
    )


CONTRACT_TEXT = """
采购合同
合同编号：HT-2026-001
甲方（买方）：星河科技（上海）有限公司
乙方（卖方）：远山软件（深圳）有限公司
合同总金额（含税）：人民币 128,000 元整
签署日期：2026年7月20日
甲方向乙方采购企业软件服务。乙方负责交付并提供一年技术支持。
""".strip()


async def main(strategy_name: str) -> None:
    api_key = os.getenv("DEEPEXI_API_KEY")
    if not api_key:
        raise SystemExit("请先设置环境变量 DEEPEXI_API_KEY")

    model = ChatOpenAI(
        model=MODEL_NAME,
        api_key=api_key,
        base_url=BASE_URL,
        temperature=0,
    )

    strategy_type = ProviderStrategy if strategy_name == "provider" else ToolStrategy
    # Production sends a JSON-schema dict whose title is always
    # ``structured_output``.  Reproduce that naming here so the demo also
    # exercises ChatService's special handling for the internal tool message.
    response_schema = ContractResult.model_json_schema()
    response_schema["title"] = "structured_output"
    agent = create_agent(
        model=model,
        tools=[get_weather],
        system_prompt=(
            "你是合同信息抽取 Agent。必须严格按以下顺序执行："
            "1. 先调用 get_weather，查询合同签署地上海的天气；"
            "2. 再从合同文本提取字段；"
            "3. 最后按结构化输出 schema 提交完整字段对象。"
            "不要直接输出普通文本，不要遗漏任何字段。"
            "结构化输出中的 weather_observation 必须与工具返回值完全一致。"
        ),
        response_format=strategy_type(response_schema),
    )

    prompt = f"合同文本如下，请完成任务：\n\n{CONTRACT_TEXT}"
    result = await agent.ainvoke({"messages": [("human", prompt)]})

    print(f"strategy={strategy_name} model={MODEL_NAME} base_url={BASE_URL}")
    print("\n消息轨迹：")
    for index, message in enumerate(result.get("messages", []), start=1):
        calls = getattr(message, "tool_calls", None) or []
        call_names = [call.get("name") for call in calls]
        content = message.content
        if isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False)
        print(
            f"{index}. type={getattr(message, 'type', type(message).__name__)} "
            f"name={getattr(message, 'name', None)} "
            f"tool_calls={call_names} content={content!r}"
        )

    structured = result.get("structured_response")
    if structured is None:
        raise RuntimeError("没有拿到 state['structured_response']，请检查模型是否支持 provider structured output")

    print("\n校验后的 structured_response：")
    if isinstance(structured, BaseModel):
        print(json.dumps(structured.model_dump(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(structured, ensure_ascii=False, indent=2))

    tool_names = [
        call.get("name")
        for message in result.get("messages", [])
        for call in (getattr(message, "tool_calls", None) or [])
    ]
    if "get_weather" not in tool_names:
        raise AssertionError(f"天气工具未被调用，实际工具调用：{tool_names}")
    print(f"\n工具调用顺序（模型原始消息中）：{tool_names}")
    print("第一轮验证通过：天气工具被调用，最终结果通过结构化 Schema 校验。")

    # Switch to a plain-chat agent while retaining the exact history from the
    # structured turn. This reproduces the production scenario where a user
    # clears the output-schema selection before sending the next message.
    # It verifies that every ToolStrategy AI tool call has its ToolMessage.
    plain_agent = create_agent(
        model=model,
        tools=[get_weather],
        system_prompt="你是助理。请直接、简洁地回答用户。",
    )
    follow_up = await plain_agent.ainvoke(
        {
            "messages": result["messages"]
            + [("human", "请用一句话确认刚才提取的合同编号。")]
        }
    )
    last_message = follow_up["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        raise AssertionError(f"普通聊天意外产生工具调用：{last_message.tool_calls}")
    print(
        "切换普通聊天验证通过："
        f"type={getattr(last_message, 'type', type(last_message).__name__)} "
        f"content={last_message.content!r}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategy",
        choices=("provider", "tool"),
        required=True,
        help="要测试的 LangChain structured-output strategy",
    )
    args = parser.parse_args()
    asyncio.run(main(args.strategy))
