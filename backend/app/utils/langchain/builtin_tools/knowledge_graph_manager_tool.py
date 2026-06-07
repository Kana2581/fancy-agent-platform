"""
knowledge_graph_manager builtin tool
子工具：
  - kg_extract_and_save   从文本提取实体/关系并存库
  - kg_search_nodes       搜索节点
  - kg_get_neighbors      获取邻居节点和关系
"""
import json
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.deps.db import get_db_session
from app.mappers.kg_edge_mapper import KGEdgeMapper
from app.mappers.kg_graph_mapper import KGGraphMapper
from app.mappers.kg_node_mapper import KGNodeMapper


# ---------- Helper ----------

async def _resolve_graph_id(user_id: int, graph_name: str, db) -> int:
    """按名称查找图谱，不存在则创建。"""
    mapper = KGGraphMapper(db)
    graph = await mapper.get_by_name(user_id, graph_name)
    if not graph:
        graph = await mapper.create_from_dict({"user_id": user_id, "name": graph_name})
    return graph.id


# ---------- Input schemas ----------

class ExtractAndSaveInput(BaseModel):
    text: str = Field(description="需要提取知识图谱的原始文本内容")
    graph_name: str = Field(default="默认图谱", description="目标图谱名称，不存在则自动创建")


class AddNodeInput(BaseModel):
    name: str = Field(description="实体名称")
    type: str = Field(default="concept", description="实体类型，如 person / organization / place / concept 等")
    description: Optional[str] = Field(default=None, description="实体描述")
    graph_name: str = Field(default="默认图谱", description="目标图谱名称")


class AddEdgeInput(BaseModel):
    source_name: str = Field(description="起点实体名称（须已存在）")
    target_name: str = Field(description="终点实体名称（须已存在）")
    relation: str = Field(description="关系标签，简洁动词或名词短语")
    graph_name: str = Field(default="默认图谱", description="目标图谱名称")


class SearchNodesInput(BaseModel):
    query: str = Field(description="搜索关键词，匹配节点名称或描述")
    type_filter: Optional[str] = Field(default=None, description="按实体类型过滤，如 person / place")
    graph_name: str = Field(default="默认图谱", description="目标图谱名称")


class GetNeighborsInput(BaseModel):
    node_name: str = Field(description="要查询邻居的实体名称")
    graph_name: str = Field(default="默认图谱", description="目标图谱名称")


class DeleteNodeInput(BaseModel):
    node_name: str = Field(description="要删除的实体名称（同时级联删除相关边）")
    graph_name: str = Field(default="默认图谱", description="目标图谱名称")


# ---------- Tool builder ----------

def build_knowledge_graph_tools(user_id: int, llm_config: Optional[dict] = None) -> List[BaseTool]:

    class ExtractAndSaveTool(BaseTool):
        name: str = "kg_extract_and_save"
        description: str = (
            "从一段文本中自动提取实体和关系，并保存到指定知识图谱。"
            "适合在用户分享大段信息后调用，自动结构化存储知识。"
            "已存在的实体会更新描述，重复的边会跳过。"
        )
        args_schema: Type[BaseModel] = ExtractAndSaveInput

        async def _arun(self, text: str, graph_name: str = "默认图谱") -> str:
            if not llm_config:
                return "当前 Agent 未配置 LLM，无法提取知识图谱。"
            try:
                from app.utils.langchain.kg_extractor import extract_kg_from_text
                result = await extract_kg_from_text(text, llm_config)
            except Exception as e:
                return f"提取失败：{e}"

            saved_nodes = []
            saved_edges = []

            async with get_db_session() as db:
                node_mapper = KGNodeMapper(db)
                edge_mapper = KGEdgeMapper(db)
                graph_id = await _resolve_graph_id(user_id, graph_name, db)

                for n in result.nodes:
                    await node_mapper.upsert(
                        graph_id=graph_id,
                        user_id=user_id,
                        name=n.name,
                        type_=n.type,
                        description=n.description,
                        properties=None,
                    )
                    saved_nodes.append(n.name)

                for e in result.edges:
                    src = await node_mapper.get_by_name(graph_id, e.source)
                    tgt = await node_mapper.get_by_name(graph_id, e.target)
                    if src and tgt:
                        dup = await edge_mapper.find_duplicate(graph_id, src.id, tgt.id, e.relation)
                        if not dup:
                            await edge_mapper.create_from_dict({
                                "user_id": user_id,
                                "graph_id": graph_id,
                                "source_node_id": src.id,
                                "target_node_id": tgt.id,
                                "relation": e.relation,
                                "properties": None,
                            })
                            saved_edges.append(f"{e.source} --[{e.relation}]--> {e.target}")

                await db.commit()

            return json.dumps(
                {"graph": graph_name, "saved_nodes": saved_nodes, "saved_edges": saved_edges},
                ensure_ascii=False,
            )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class AddNodeTool(BaseTool):
        name: str = "kg_add_node"
        description: str = "手动添加或更新一个实体节点到指定知识图谱。同名节点会更新描述。"
        args_schema: Type[BaseModel] = AddNodeInput

        async def _arun(self, name: str, type: str = "concept", description: Optional[str] = None, graph_name: str = "默认图谱") -> str:
            async with get_db_session() as db:
                graph_id = await _resolve_graph_id(user_id, graph_name, db)
                node = await KGNodeMapper(db).upsert(
                    graph_id=graph_id,
                    user_id=user_id,
                    name=name,
                    type_=type,
                    description=description,
                    properties=None,
                )
                await db.commit()
            return json.dumps({"id": node.id, "name": node.name, "type": node.type, "graph": graph_name}, ensure_ascii=False)

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class AddEdgeTool(BaseTool):
        name: str = "kg_add_edge"
        description: str = "在两个已存在的实体之间添加关系边。重复关系会跳过。"
        args_schema: Type[BaseModel] = AddEdgeInput

        async def _arun(self, source_name: str, target_name: str, relation: str, graph_name: str = "默认图谱") -> str:
            async with get_db_session() as db:
                node_mapper = KGNodeMapper(db)
                edge_mapper = KGEdgeMapper(db)
                graph_id = await _resolve_graph_id(user_id, graph_name, db)
                src = await node_mapper.get_by_name(graph_id, source_name)
                tgt = await node_mapper.get_by_name(graph_id, target_name)
                if not src:
                    return f"实体「{source_name}」不存在于图谱「{graph_name}」，请先添加节点。"
                if not tgt:
                    return f"实体「{target_name}」不存在于图谱「{graph_name}」，请先添加节点。"
                dup = await edge_mapper.find_duplicate(graph_id, src.id, tgt.id, relation)
                if dup:
                    return f"关系「{source_name} --[{relation}]--> {target_name}」已存在。"
                edge = await edge_mapper.create_from_dict({
                    "user_id": user_id,
                    "graph_id": graph_id,
                    "source_node_id": src.id,
                    "target_node_id": tgt.id,
                    "relation": relation,
                    "properties": None,
                })
                await db.commit()
            return json.dumps({"id": edge.id, "relation": relation, "graph": graph_name}, ensure_ascii=False)

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class SearchNodesTool(BaseTool):
        name: str = "kg_search_nodes"
        description: str = "在指定知识图谱中按名称/描述模糊搜索实体节点，可按类型过滤。"
        args_schema: Type[BaseModel] = SearchNodesInput

        async def _arun(self, query: str, type_filter: Optional[str] = None, graph_name: str = "默认图谱") -> str:
            async with get_db_session() as db:
                graph = await KGGraphMapper(db).get_by_name(user_id, graph_name)
                if not graph:
                    return f"图谱「{graph_name}」不存在。"
                nodes = await KGNodeMapper(db).search(graph.id, query, type_filter)
            return json.dumps(
                [{"id": n.id, "name": n.name, "type": n.type, "description": n.description or ""} for n in nodes],
                ensure_ascii=False,
            )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class GetNeighborsTool(BaseTool):
        name: str = "kg_get_neighbors"
        description: str = "获取指定实体的所有相邻节点和关系，了解该实体在图谱中的连接情况。"
        args_schema: Type[BaseModel] = GetNeighborsInput

        async def _arun(self, node_name: str, graph_name: str = "默认图谱") -> str:
            async with get_db_session() as db:
                node_mapper = KGNodeMapper(db)
                edge_mapper = KGEdgeMapper(db)
                graph = await KGGraphMapper(db).get_by_name(user_id, graph_name)
                if not graph:
                    return f"图谱「{graph_name}」不存在。"
                node = await node_mapper.get_by_name(graph.id, node_name)
                if not node:
                    return f"实体「{node_name}」不存在于图谱「{graph_name}」。"
                edges = await edge_mapper.get_neighbors(graph.id, node.id)

                neighbor_ids = set()
                for e in edges:
                    neighbor_ids.add(e.source_node_id)
                    neighbor_ids.add(e.target_node_id)
                neighbor_ids.discard(node.id)

                node_id_to_name = {node.id: node.name}
                neighbors = []
                for n in await node_mapper.get_by_ids(list(neighbor_ids)):
                    node_id_to_name[n.id] = n.name
                    neighbors.append({"name": n.name, "type": n.type})

                relations = [
                    {
                        "source": node_id_to_name[e.source_node_id],
                        "target": node_id_to_name[e.target_node_id],
                        "relation": e.relation,
                    }
                    for e in edges
                    if e.source_node_id in node_id_to_name and e.target_node_id in node_id_to_name
                ]

            return json.dumps(
                {"node": node_name, "graph": graph_name, "neighbors": neighbors, "relations": relations},
                ensure_ascii=False,
            )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class DeleteNodeTool(BaseTool):
        name: str = "kg_delete_node"
        description: str = "删除指定实体节点，同时级联删除所有与该实体相关的边。"
        args_schema: Type[BaseModel] = DeleteNodeInput

        async def _arun(self, node_name: str, graph_name: str = "默认图谱") -> str:
            async with get_db_session() as db:
                node_mapper = KGNodeMapper(db)
                graph_id = await _resolve_graph_id(user_id, graph_name, db)
                node = await node_mapper.get_by_name(graph_id, node_name)
                if not node:
                    return f"实体「{node_name}」不存在于图谱「{graph_name}」。"
                await node_mapper.delete_by_id(node.id)
                await db.commit()
            return f"已删除实体「{node_name}」及相关边（图谱：{graph_name}）。"

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    return [
        ExtractAndSaveTool(),
        SearchNodesTool(),
        GetNeighborsTool(),
    ]
