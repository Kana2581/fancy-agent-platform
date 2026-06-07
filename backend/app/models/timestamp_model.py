from sqlalchemy import (
    Column,
    DateTime,
)
from datetime import datetime
class TimestampMixin:
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
        nullable=False,
    )
