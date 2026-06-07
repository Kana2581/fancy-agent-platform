from datetime import datetime, UTC

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String(32), nullable=False, index=True)
    revoked = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
