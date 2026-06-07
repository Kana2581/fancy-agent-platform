# app/mapper/chat_file_mapper.py
from typing import Optional, List, Dict
from sqlalchemy import select
from app.mappers.base_mapper import BaseMapper
from app.models.chat_file import ChatFile


class ChatFileMapper(BaseMapper[ChatFile]):
    model = ChatFile

    async def list_by_session(self, session_id: int) -> List[ChatFile]:
        result = await self.db.execute(
            select(ChatFile).where(ChatFile.session_id == session_id)
        )
        return result.scalars().all()

    async def list_by_user(self, user_id: int) -> List[ChatFile]:
        result = await self.db.execute(
            select(ChatFile).where(ChatFile.upload_user_id == user_id)
        )
        return result.scalars().all()

    async def get_by_md5(self, md5: str) -> Optional[ChatFile]:
        """秒传用：相同 md5 直接复用"""
        result = await self.db.execute(
            select(ChatFile).where(ChatFile.md5 == md5)
        )
        return result.scalars().first()

    async def get_workspace_file(
        self,
        session_id: str,
        user_id: int,
        object_key: str,
    ) -> Optional[ChatFile]:
        """ws_present 去重用：定位同一 session 下同一物理文件的已登记行。"""
        result = await self.db.execute(
            select(ChatFile).where(
                ChatFile.session_id == session_id,
                ChatFile.upload_user_id == user_id,
                ChatFile.object_key == object_key,
                ChatFile.storage_type == "workspace",
            )
        )
        return result.scalars().first()

    async def update_parse_status(
        self,
        file_id: int,
        status: int,
        error: str | None = None,
    ) -> None:
        await self.update_by_id(file_id, {"parse_status": status, "parse_error": error})


    async def get_by_ids(self, file_ids: List[int]) -> Dict[int, ChatFile]:
        """
        批量查询 file_id -> ChatFile 映射。
        1 次 SQL。
        """
        if not file_ids:
            return {}
        stmt = select(ChatFile).where(ChatFile.id.in_(file_ids))
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return {row.id: row for row in rows}