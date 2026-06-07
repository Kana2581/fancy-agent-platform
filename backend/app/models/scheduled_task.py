from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class ScheduledTask(TimestampMixin, Base):
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    agent_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    instruction = Column(Text, nullable=False)
    schedule_type = Column(String(20), nullable=False)   # daily | weekly | monthly
    schedule_time = Column(String(5), nullable=False)    # HH:MM
    schedule_day = Column(Integer, nullable=True)        # weekly:0-6, monthly:1-31
    timezone = Column(String(50), nullable=False, default="Asia/Shanghai")
    is_enabled = Column(Boolean, nullable=False, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True, index=True)
