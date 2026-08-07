from sqlalchemy import Column, Integer, JSON, String, Text

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class StructuredOutputSchema(Base, TimestampMixin):
    __tablename__ = "structured_output_schemas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    field_config = Column(JSON, nullable=False)
