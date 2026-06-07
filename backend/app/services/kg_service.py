from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.kg_edge_mapper import KGEdgeMapper
from app.mappers.kg_graph_mapper import KGGraphMapper
from app.mappers.kg_node_mapper import KGNodeMapper
from app.models.kg_edge import KGEdge
from app.models.kg_graph import KGGraph
from app.models.kg_node import KGNode
from app.schemas.kg_schema import (
    KGEdgeCreate,
    KGEdgeOut,
    KGGraphCreate,
    KGGraphDataOut,
    KGGraphUpdate,
    KGNodeCreate,
    KGNodeOut,
    KGNodeUpdate,
)


class KGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph_mapper = KGGraphMapper(db)
        self.node_mapper = KGNodeMapper(db)
        self.edge_mapper = KGEdgeMapper(db)

    # ---------- Graphs ----------

    async def list_graphs(self, user_id: int) -> List[KGGraph]:
        return await self.graph_mapper.list_by_user(user_id)

    async def get_graph(self, graph_id: int) -> Optional[KGGraph]:
        return await self.graph_mapper.get_by_id(graph_id)

    async def create_graph(self, user_id: int, data: KGGraphCreate) -> KGGraph:
        graph = await self.graph_mapper.create_from_dict({
            "user_id": user_id,
            "name": data.name,
            "description": data.description,
        })
        await self.db.commit()
        return graph

    async def update_graph(self, graph_id: int, data: KGGraphUpdate) -> Optional[KGGraph]:
        graph = await self.graph_mapper.update_by_id(graph_id, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return graph

    async def delete_graph(self, graph_id: int) -> bool:
        # 节点和边通过 FK CASCADE 自动删除
        res = await self.graph_mapper.delete_by_id(graph_id)
        await self.db.commit()
        return res

    # ---------- Nodes ----------

    async def list_nodes(
        self, graph_id: int, search: Optional[str] = None, type_filter: Optional[str] = None
    ) -> List[KGNode]:
        if search or type_filter:
            return await self.node_mapper.search(graph_id, search or "", type_filter)
        return await self.node_mapper.list_by_filters({"graph_id": graph_id})

    async def get_node(self, node_id: int) -> Optional[KGNode]:
        return await self.node_mapper.get_by_id(node_id)

    async def create_node(self, user_id: int, graph_id: int, data: KGNodeCreate) -> KGNode:
        node = await self.node_mapper.create_from_dict({
            "user_id": user_id,
            "graph_id": graph_id,
            **data.model_dump(),
        })
        await self.db.commit()
        return node

    async def update_node(self, node_id: int, data: KGNodeUpdate) -> Optional[KGNode]:
        node = await self.node_mapper.update_by_id(node_id, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return node

    async def delete_node(self, node_id: int) -> bool:
        res = await self.node_mapper.delete_by_id(node_id)
        await self.db.commit()
        return res

    # ---------- Edges ----------

    async def list_edges(self, graph_id: int) -> List[KGEdge]:
        return await self.edge_mapper.list_by_graph(graph_id)

    async def create_edge(self, user_id: int, graph_id: int, data: KGEdgeCreate) -> KGEdge:
        source_id = data.source_node_id
        target_id = data.target_node_id

        if source_id is None and data.source_name:
            node = await self.node_mapper.get_by_name(graph_id, data.source_name)
            if node:
                source_id = node.id
        if target_id is None and data.target_name:
            node = await self.node_mapper.get_by_name(graph_id, data.target_name)
            if node:
                target_id = node.id

        if source_id is None or target_id is None:
            raise ValueError("无法找到源节点或目标节点")

        dup = await self.edge_mapper.find_duplicate(graph_id, source_id, target_id, data.relation)
        if dup:
            return dup

        edge = await self.edge_mapper.create_from_dict({
            "user_id": user_id,
            "graph_id": graph_id,
            "source_node_id": source_id,
            "target_node_id": target_id,
            "relation": data.relation,
            "properties": data.properties,
        })
        await self.db.commit()
        return edge

    async def delete_edge(self, edge_id: int) -> bool:
        res = await self.edge_mapper.delete_by_id(edge_id)
        await self.db.commit()
        return res

    # ---------- Full graph ----------

    async def get_full_graph(self, graph_id: int) -> KGGraphDataOut:
        nodes = await self.node_mapper.list_by_filters({"graph_id": graph_id}, limit=2000)
        edges = await self.edge_mapper.list_by_graph(graph_id)
        return KGGraphDataOut(
            nodes=[KGNodeOut.model_validate(n) for n in nodes],
            edges=[KGEdgeOut.model_validate(e) for e in edges],
        )

    async def get_neighbors(self, graph_id: int, node_id: int):
        edges = await self.edge_mapper.get_neighbors(graph_id, node_id)
        neighbor_ids = set()
        for e in edges:
            neighbor_ids.add(e.source_node_id)
            neighbor_ids.add(e.target_node_id)
        neighbor_ids.discard(node_id)

        nodes = []
        for nid in neighbor_ids:
            n = await self.node_mapper.get_by_id(nid)
            if n:
                nodes.append(n)

        return {"nodes": nodes, "edges": edges}

    # ---------- Export ----------

    async def export_to_cypher(self, graph: KGGraph) -> str:
        nodes = await self.node_mapper.list_by_filters({"graph_id": graph.id}, limit=100000)
        edges = await self.edge_mapper.list_by_graph(graph.id)
        return _build_cypher_script(graph, nodes, edges)


# ---------- Cypher helpers ----------

def _cypher_escape_str(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\r", "")
        .replace("\n", "\\n")
    )


def _cypher_ident(s: str) -> str:
    # Backtick-quoted identifier; escape embedded backticks by doubling.
    safe = (s or "Entity").replace("`", "``")
    return f"`{safe}`"


def _cypher_props(pairs: list[tuple[str, object]]) -> str:
    parts = []
    for key, value in pairs:
        if value is None:
            continue
        if isinstance(value, bool):
            parts.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            parts.append(f"{key}: {value}")
        else:
            parts.append(f"{key}: '{_cypher_escape_str(str(value))}'")
    return "{" + ", ".join(parts) + "}"


def _build_cypher_script(graph: KGGraph, nodes: List[KGNode], edges: List[KGEdge]) -> str:
    lines: List[str] = [
        "// Fancy Agent Knowledge Graph Export (Neo4j Cypher)",
        f"// Graph: {graph.name}",
        f"// Nodes: {len(nodes)}, Edges: {len(edges)}",
        "// Usage: paste into Neo4j Browser, or run with `cypher-shell < graph.cypher`",
        "// Note: nodes are tagged with `_import_id` so edges can match them.",
        "//       Remove with: MATCH (n) WHERE n._import_id IS NOT NULL REMOVE n._import_id;",
        "",
        "// ===== Nodes =====",
    ]

    for n in nodes:
        label = _cypher_ident(n.type)
        props = _cypher_props([
            ("_import_id", n.id),
            ("name", n.name),
            ("description", n.description),
        ])
        lines.append(f"CREATE (:{label} {props});")

    if edges:
        lines.append("")
        lines.append("// ===== Edges =====")
        for e in edges:
            rel = _cypher_ident(e.relation)
            lines.append(
                f"MATCH (a {{_import_id: {e.source_node_id}}}), "
                f"(b {{_import_id: {e.target_node_id}}}) "
                f"CREATE (a)-[:{rel}]->(b);"
            )

    return "\n".join(lines) + "\n"
