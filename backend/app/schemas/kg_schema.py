from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ==================== Graph ====================

class KGGraphCreate(BaseModel):
    name: str
    description: Optional[str] = None


class KGGraphUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class KGGraphOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ==================== Node ====================

class KGNodeCreate(BaseModel):
    name: str
    type: str = "concept"
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class KGNodeUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class KGNodeOut(BaseModel):
    id: int
    user_id: int
    graph_id: int
    name: str
    type: str
    description: Optional[str]
    properties: Optional[Dict[str, Any]]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ==================== Edge ====================

class KGEdgeCreate(BaseModel):
    source_node_id: Optional[int] = None
    target_node_id: Optional[int] = None
    source_name: Optional[str] = None
    target_name: Optional[str] = None
    relation: str
    properties: Optional[Dict[str, Any]] = None


class KGEdgeOut(BaseModel):
    id: int
    user_id: int
    graph_id: int
    source_node_id: int
    target_node_id: int
    relation: str
    properties: Optional[Dict[str, Any]]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ==================== Compound ====================

class KGGraphDataOut(BaseModel):
    nodes: List[KGNodeOut]
    edges: List[KGEdgeOut]


class KGExtractRequest(BaseModel):
    text: str
    agent_id: int


class KGExtractPreview(BaseModel):
    nodes: List[KGNodeCreate]
    edges: List[KGEdgeCreate]
