# app/models/chat_file.py
from sqlalchemy import  String, Text, Integer, DateTime,SmallInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class ChatFile(Base,TimestampMixin):
    __tablename__ = "chat_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_ext: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    storage_type: Mapped[str] = mapped_column(String(20), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    md5: Mapped[str | None] = mapped_column(String(64))
    upload_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(36))
    parse_status: Mapped[int] = mapped_column(Integer, default=0)
    parse_error: Mapped[str | None] = mapped_column(Text)
