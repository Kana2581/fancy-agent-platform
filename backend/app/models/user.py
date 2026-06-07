from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func, text

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class User(Base,TimestampMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("1"))
