from sqlalchemy import Column, ForeignKey, Integer, JSON, String

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class KGEdge(Base, TimestampMixin):
    __tablename__ = "kg_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    graph_id = Column(Integer, ForeignKey("kg_graphs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id = Column(Integer, ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    relation = Column(String(200), nullable=False)
    properties = Column(JSON, nullable=True)
