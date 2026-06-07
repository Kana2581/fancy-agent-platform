from sqlalchemy import Boolean, Column, Integer, String, Text

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class HelpDocument(Base, TimestampMixin):
    __tablename__ = "help_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    title = Column(String(160), nullable=False)
    summary = Column(String(800), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(80), nullable=True, index=True)
    doc_type = Column(String(50), nullable=False, index=True)
    route = Column(String(120), nullable=True)
    icon_key = Column(String(80), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
