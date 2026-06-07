from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class KGGraph(Base, TimestampMixin):
    __tablename__ = "kg_graphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
