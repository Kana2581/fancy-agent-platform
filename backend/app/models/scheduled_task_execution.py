from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class ScheduledTaskExecution(TimestampMixin, Base):
    __tablename__ = "scheduled_task_executions"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), nullable=False)          # running | success | failed
    result = Column(Text, nullable=True)
    email_sent = Column(Boolean, nullable=False, default=False)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
