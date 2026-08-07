from sqlalchemy import Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


SKILL_SCOPE_SYSTEM = "system"
SKILL_SCOPE_USER = "user"


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("user_id", "scope", "name", name="uq_skill_scope_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    # 分层：system (平台预设，user_id=0) / user (用户自建)
    scope = Column(String(20), nullable=False, default=SKILL_SCOPE_USER, server_default=SKILL_SCOPE_USER, index=True)

    # Filesystem package metadata.  ``content`` and ``files`` remain for
    # backwards-compatible reads while packages are migrated incrementally.
    source_type = Column(String(16), nullable=False, default="db", server_default="db")
    package_path = Column(String(512), nullable=True)
    package_status = Column(String(16), nullable=False, default="ready", server_default="ready")
    content_hash = Column(String(64), nullable=True)
    last_scanned_at = Column(String(40), nullable=True)

    # 随包携带的文本文件（脚本/模板/说明）。selectin 异步预加载，避免 lazy-load 报错。
    files = relationship(
        "SkillFile",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SkillFile.path",
    )
