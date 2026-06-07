from sqlalchemy import Column, Integer, String, JSON, Text

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class ApiTool(Base, TimestampMixin):
    __tablename__ = "api_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False, default="GET")
    headers = Column(JSON, nullable=True)           # dict[str, str]
    param_location = Column(String(20), nullable=False, default="query")
    fixed_params = Column(JSON, nullable=True)      # nested dict
    tool_params = Column(JSON, nullable=True)       # list[ParamConfig]
    response_extract = Column(JSON, nullable=True)  # list[ResponseExtract]
    response_max_chars = Column(Integer, nullable=False, default=2000)
