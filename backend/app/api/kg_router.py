from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse

from app.deps.service import get_kg_service
from app.deps.user import get_current_user
from app.schemas.kg_schema import (
    KGEdgeCreate,
    KGEdgeOut,
    KGExtractRequest,
    KGExtractPreview,
    KGGraphCreate,
    KGGraphDataOut,
    KGGraphOut,
    KGGraphUpdate,
    KGNodeCreate,
    KGNodeOut,
    KGNodeUpdate,
)
from app.services.kg_service import KGService

router = APIRouter(prefix="/knowledge-graph", tags=["KnowledgeGraph"])


# ==================== Graphs ====================

@router.get("/graphs", response_model=List[KGGraphOut])
async def list_graphs(
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    return await service.list_graphs(user_id)


@router.post("/graphs", response_model=KGGraphOut)
async def create_graph(
    data: KGGraphCreate,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    return await service.create_graph(user_id, data)


@router.put("/graphs/{graph_id}", response_model=KGGraphOut)
async def update_graph(
    graph_id: int,
    data: KGGraphUpdate,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")
    return await service.update_graph(graph_id, data)


@router.delete("/graphs/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_graph(
    graph_id: int,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")
    await service.delete_graph(graph_id)


# ==================== Nodes ====================

@router.get("/graphs/{graph_id}/nodes", response_model=List[KGNodeOut])
async def list_nodes(
    graph_id: int,
    search: Optional[str] = None,
    type: Optional[str] = None,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")
    return await service.list_nodes(graph_id, search=search, type_filter=type)


@router.post("/graphs/{graph_id}/nodes", response_model=KGNodeOut)
async def create_node(
    graph_id: int,
    data: KGNodeCreate,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")
    return await service.create_node(user_id, graph_id, data)


@router.put("/nodes/{node_id}", response_model=KGNodeOut)
async def update_node(
    node_id: int,
    data: KGNodeUpdate,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    node = await service.get_node(node_id)
    if not node or node.user_id != user_id:
        raise HTTPException(status_code=404, detail="Node not found")
    return await service.update_node(node_id, data)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: int,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    node = await service.get_node(node_id)
    if not node or node.user_id != user_id:
        raise HTTPException(status_code=404, detail="Node not found")
    await service.delete_node(node_id)


# ==================== Edges ====================

@router.get("/graphs/{graph_id}/edges", response_model=List[KGEdgeOut])
async def list_edges(
    graph_id: int,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")
    return await service.list_edges(graph_id)


@router.post("/graphs/{graph_id}/edges", response_model=KGEdgeOut)
async def create_edge(
    graph_id: int,
    data: KGEdgeCreate,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")
    try:
        return await service.create_edge(user_id, graph_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(
    edge_id: int,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    await service.delete_edge(edge_id)


# ==================== Full graph ====================

@router.get("/graphs/{graph_id}/graph", response_model=KGGraphDataOut)
async def get_full_graph(
    graph_id: int,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")
    return await service.get_full_graph(graph_id)


# ==================== Export ====================

@router.get("/graphs/{graph_id}/export/cypher", response_class=PlainTextResponse)
async def export_graph_cypher(
    graph_id: int,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")
    content = await service.export_to_cypher(graph)
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in graph.name) or f"graph-{graph.id}"
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.cypher"'},
    )


# ==================== Extract ====================

@router.post("/graphs/{graph_id}/extract", response_model=KGExtractPreview)
async def extract_from_text(
    graph_id: int,
    req: KGExtractRequest,
    user_id: int = Depends(get_current_user),
    service: KGService = Depends(get_kg_service),
):
    graph = await service.get_graph(graph_id)
    if not graph or graph.user_id != user_id:
        raise HTTPException(status_code=404, detail="Graph not found")

    from app.utils.langchain.kg_extractor import extract_kg_from_text
    from app.deps.db import get_db_session
    from app.mappers.agent_mapper import AgentMapper

    async with get_db_session() as db:
        agent_data = await AgentMapper(db).get_full_agent(req.agent_id, user_id)

    if not agent_data or not agent_data.get("llm"):
        raise HTTPException(status_code=400, detail="Agent 未找到或未配置 LLM")

    try:
        result = await extract_kg_from_text(req.text, agent_data["llm"])
        return KGExtractPreview(
            nodes=[
                KGNodeCreate(name=n.name, type=n.type, description=n.description)
                for n in result.nodes
            ],
            edges=[
                KGEdgeCreate(source_name=e.source, target_name=e.target, relation=e.relation)
                for e in result.edges
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取失败: {e}")
