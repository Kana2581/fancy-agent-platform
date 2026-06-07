from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class SkillFile(Base, TimestampMixin):
    """技能随包携带的文本文件（脚本/模板/说明）。

    use_skill 时物化到会话工作区 .skills/<name>/，agent 用 python_exec 运行。
    随 skill 级联删除（含 session 级技能在会话结束时的清理）。
    """
    __tablename__ = "skill_files"
    __table_args__ = (
        UniqueConstraint("skill_id", "path", name="uq_skill_file_path"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path = Column(String(255), nullable=False)  # 相对路径，如 profile.py 或 templates/a.txt
    content = Column(Text, nullable=False)
    size = Column(Integer, nullable=False, default=0)
