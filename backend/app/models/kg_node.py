from sqlalchemy import Column, ForeignKey, Integer, JSON, String, Text, UniqueConstraint

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class KGNode(Base, TimestampMixin):
    __tablename__ = "kg_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    graph_id = Column(Integer, ForeignKey("kg_graphs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(100), nullable=False, default="concept")
    description = Column(Text, nullable=True)
    properties = Column(JSON, nullable=True)

    __table_args__ = (UniqueConstraint("graph_id", "name", name="uq_kg_node_graph_name"),)
