import json
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.deps.db import get_db_session
from app.mappers.user_memory_mapper import UserMemoryMapper


class SaveMemoryInput(BaseModel):
    key: str = Field(description="记忆的唯一标识符（简短英文或中文词组），同名记忆会被覆盖。建议用能体现内容的描述性名称，如 preferred_language、工作习惯_会议时间")
    content: str = Field(description="记忆的正文内容。core 级应简短精炼（一两句话），normal 级可详细")
    memory_type: str = Field(
        default="normal",
        description=(
            '记忆级别。'
            '"core"：核心记忆，会自动注入每次对话的系统提示词，必须简短精炼（不超过30字）；'
            '适合存用户身份、语言偏好、沟通风格等高频基础信息。'
            '"normal"：普通记忆，需主动调用查询工具才能读取；适合存事件、详细背景、临时信息。'
            '【重要】凡是用户提到的个人偏好、习惯、身份信息、重要约定，都应主动存为记忆，不要等用户主动要求。'
        ),
    )
    category: Optional[str] = Field(default=None, description="分类标签，可选，如：偏好、工作、生活、约定")


class GetMemoryInput(BaseModel):
    key: str = Field(description="要查询的记忆标识符。若不确定准确 key，请先调用 list_memories 查看所有 key 后再操作")


class ListMemoriesInput(BaseModel):
    category: Optional[str] = Field(default=None, description="按分类过滤，不填则返回全部")


class DeleteMemoryInput(BaseModel):
    key: str = Field(description="要删除的记忆标识符")


def build_memory_manager_tools(user_id: int) -> List[BaseTool]:
    class SaveMemoryTool(BaseTool):
        name: str = "save_memory"
        description: str = (
            "保存或更新一条长期记忆。同名记忆会被覆盖（upsert 语义）。"
            "【主动存记忆的时机】：用户提到个人偏好（语言、风格、习惯）、身份信息、重要约定、工作背景时，"
            "应主动调用此工具存储，无需等用户明确要求。"
            "core 级记忆（简短，≤30字）会自动注入系统提示词，适合高频基础信息；"
            "normal 级适合详细内容，需主动查询。"
        )
        args_schema: Type[BaseModel] = SaveMemoryInput

        async def _arun(
            self,
            key: str,
            content: str,
            memory_type: str = "normal",
            category: Optional[str] = None,
        ) -> str:
            if memory_type not in ("core", "normal"):
                memory_type = "normal"
            async with get_db_session() as db:
                memory = await UserMemoryMapper(db).upsert(
                    user_id=user_id,
                    key=key,
                    content=content,
                    memory_type=memory_type,
                    category=category,
                )
                await db.commit()
                return json.dumps(
                    {"id": memory.id, "key": memory.key, "memory_type": memory.memory_type},
                    ensure_ascii=False,
                )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class GetMemoryTool(BaseTool):
        name: str = "get_memory"
        description: str = (
            "按标识符精确查找一条记忆，返回完整内容。"
            "若精确 key 未找到，会自动进行模糊匹配并返回候选列表。"
            "若不确定准确 key，请先调用 list_memories 查看所有 key 后再操作。"
        )
        args_schema: Type[BaseModel] = GetMemoryInput

        async def _arun(self, key: str) -> str:
            async with get_db_session() as db:
                mapper = UserMemoryMapper(db)
                memory = await mapper.get_by_key(user_id, key)
                if memory:
                    return json.dumps(
                        {
                            "key": memory.key,
                            "content": memory.content,
                            "memory_type": memory.memory_type,
                            "category": memory.category or "",
                        },
                        ensure_ascii=False,
                    )
                candidates = await mapper.search_by_keyword(user_id, key)
                if not candidates:
                    return f"未找到标识符为「{key}」的记忆，也无相似记忆。"
                candidate_list = [
                    {"key": m.key, "summary": m.content[:80] + ("…" if len(m.content) > 80 else "")}
                    for m in candidates
                ]
                return json.dumps(
                    {
                        "error": f"未找到精确匹配「{key}」，找到以下相似记忆，请用准确 key 重新查询或直接使用以下内容：",
                        "candidates": candidate_list,
                    },
                    ensure_ascii=False,
                )

        def _run(self, key: str) -> str:
            raise NotImplementedError("Use async version")

    class ListMemoriesTool(BaseTool):
        name: str = "list_memories"
        description: str = (
            "列出 normal 级记忆摘要（不含完整内容，需完整内容请用 get_memory）。"
            "core 级记忆已自动注入系统提示词，无需通过此工具查询。"
            "可按分类过滤。对话开始时如需了解用户背景，可先调用此工具浏览已有记忆。"
        )
        args_schema: Type[BaseModel] = ListMemoriesInput

        async def _arun(
            self,
            category: Optional[str] = None,
        ) -> str:
            async with get_db_session() as db:
                memories = await UserMemoryMapper(db).list_by_user(
                    user_id, memory_type="normal", category=category
                )
                return json.dumps(
                    [
                        {
                            "key": m.key,
                            "memory_type": m.memory_type,
                            "category": m.category or "",
                            "summary": m.content[:100] + ("…" if len(m.content) > 100 else ""),
                        }
                        for m in memories
                    ],
                    ensure_ascii=False,
                )

        def _run(self, category: Optional[str] = None) -> str:
            raise NotImplementedError("Use async version")

    class DeleteMemoryTool(BaseTool):
        name: str = "delete_memory"
        description: str = (
            "按标识符删除一条记忆。"
            "若精确 key 未找到，会自动返回相似 key 候选列表，不会误删。"
            "若不确定准确 key，请先调用 list_memories 查看所有 key 后再操作。"
        )
        args_schema: Type[BaseModel] = DeleteMemoryInput

        async def _arun(self, key: str) -> str:
            async with get_db_session() as db:
                mapper = UserMemoryMapper(db)
                memory = await mapper.get_by_key(user_id, key)
                if not memory:
                    candidates = await mapper.search_by_keyword(user_id, key)
                    if not candidates:
                        return f"未找到标识符为「{key}」的记忆，无需删除。"
                    keys = [m.key for m in candidates]
                    return json.dumps(
                        {"error": f"未找到精确匹配「{key}」，相似 key：{keys}，请用准确 key 重新调用。"},
                        ensure_ascii=False,
                    )
                await mapper.delete_by_id(memory.id)
                await db.commit()
                return f"已删除记忆「{key}」。"

        def _run(self, key: str) -> str:
            raise NotImplementedError("Use async version")

    return [SaveMemoryTool(), GetMemoryTool(), ListMemoriesTool(), DeleteMemoryTool()]
