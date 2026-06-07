"""
知识图谱提取工具
- 供 kg_router 的 /extract 接口调用（预览）
- 供 knowledge_graph_manager builtin tool 调用（提取并存储）
"""
from typing import List, Optional

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.schemas.dto.langchian import ValidChatModel


EXTRACT_SYSTEM_PROMPT = """你是一个专业的知识图谱构建助手。
请从用户提供的文本中提取所有重要的实体和它们之间的关系，构建结构化的知识图谱。

提取原则：
1. 节点（实体）：提取人名、组织、地点、概念、事件、产品等具体实体，避免提取泛化词汇
2. 边（关系）：提取实体间有意义的关系，关系标签应简洁明确
3. 保持实体名称与原文一致，不要翻译或修改
4. 只提取文本中明确存在的信息，不做推断

请严格按以下 JSON 格式输出，不要输出任何其他内容：
{
  "nodes": [
    {"name": "实体名称", "type": "实体类型", "description": "简短描述或null"}
  ],
  "edges": [
    {"source": "起点实体名称", "target": "终点实体名称", "relation": "关系标签"}
  ]
}"""


class _ExtractedNode(BaseModel):
    name: str
    type: str = "concept"
    description: Optional[str] = None


class _ExtractedEdge(BaseModel):
    source: str
    target: str
    relation: str


class _KGExtractResult(BaseModel):
    nodes: List[_ExtractedNode] = Field(default_factory=list)
    edges: List[_ExtractedEdge] = Field(default_factory=list)


async def extract_kg_from_text(text: str, llm_config: dict) -> "_KGExtractResult":
    """
    llm_config: 原始 agent llm 字典（含 provider/model_name/base_url/api_key）
    返回 _KGExtractResult（nodes + edges，仅用于预览或存储）
    """
    model_config = ValidChatModel.model_validate(llm_config)
    llm = init_chat_model(**model_config.model_dump())
    structured_llm = llm.with_structured_output(_KGExtractResult, method="json_mode")
    messages = [
        SystemMessage(content=EXTRACT_SYSTEM_PROMPT),
        HumanMessage(content=text),
    ]
    return await structured_llm.ainvoke(messages)
