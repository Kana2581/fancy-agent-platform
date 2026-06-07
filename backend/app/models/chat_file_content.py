from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.timestamp_model import TimestampMixin
from app.utils.db_compat import LargeText

class ChatFileContent(Base,TimestampMixin):
    __tablename__ = "chat_file_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    content: Mapped[str] = mapped_column(LargeText, nullable=False)
    content_length: Mapped[int | None] = mapped_column(Integer)
