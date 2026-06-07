import shutil
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.mappers.chat_file_mapper import ChatFileMapper
from app.mappers.session_mapper import SessionMapper
from app.mappers.skill_mapper import SkillMapper
from app.models.chat_file import ChatFile
from app.models.session import Session
from app.schemas.session_schema import SessionCreate, SessionUpdate
from app.utils.workspace_path import get_workspace_root

logger = get_logger(__name__)


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = SessionMapper(db)

    async def get(self, session_id: str) -> Optional[Session]:
        return await self.mapper.get_by_id(session_id)

    async def list(
        self,
        user_id: int,
        agent_id: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Session], int]:
        return await self.mapper.list_with_search(
            user_id=user_id,
            agent_id=agent_id,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    async def create(
        self,
        agent_id: int,
        user_id: int,
        title: Optional[str] = None,
        is_active: bool = True,
    ) -> Session:
        data = {
            "agent_id": agent_id,
            "user_id": user_id,
            "title": title,
            "is_active": is_active,
            "id": str(uuid4()),
        }
        res = await self.mapper.create_from_dict(data)
        await self.db.commit()
        return res

    async def update(
        self,
        session_id: str,
        data: SessionUpdate,
    ) -> Optional[Session]:
        res = await self.mapper.update_by_id(
            session_id,
            data.dict(exclude_unset=True),
        )
        await self.db.commit()
        return res

    async def mark_auto_title_attempted(
        self,
        session_id: str,
        title: Optional[str] = None,
    ) -> Optional[Session]:
        data = {"auto_title_generated": True}
        if title:
            data["title"] = title
        res = await self.mapper.update_by_id(session_id, data)
        await self.db.commit()
        return res

    async def delete(self, session_id: str) -> bool:
        session = await self.mapper.get_by_id(session_id)
        if session:
            await self._cleanup_workspace(session.user_id, session_id)
        res = await self.mapper.delete_by_id(session_id)
        await self.db.commit()
        return res

    async def _cleanup_workspace(self, user_id: int, session_id: str) -> None:
        """删 session 时联动清理：workspace 物理目录、workspace ChatFile 行、session 级 Skill 行。"""
        try:
            ws_root = get_workspace_root(user_id, session_id)
            if ws_root.exists():
                shutil.rmtree(ws_root, ignore_errors=True)
        except Exception as e:
            logger.warning(f"清理 workspace 目录失败 session={session_id}: {e}")

        try:
            rows = await self.db.execute(
                select(ChatFile).where(
                    ChatFile.session_id == session_id,
                    ChatFile.storage_type == "workspace",
                )
            )
            file_ids = [r.id for r in rows.scalars().all()]
            if file_ids:
                await self.db.execute(delete(ChatFile).where(ChatFile.id.in_(file_ids)))
        except Exception as e:
            logger.warning(f"清理 workspace ChatFile 行失败 session={session_id}: {e}")

        try:
            await SkillMapper(self.db).delete_session_skills(session_id)
        except Exception as e:
            logger.warning(f"清理 session skills 失败 session={session_id}: {e}")
