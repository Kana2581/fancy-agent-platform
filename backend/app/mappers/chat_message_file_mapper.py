from typing import List, Optional, Dict

from sqlalchemy import select, delete

from app.mappers.base_mapper import BaseMapper
from app.models.chat_message_file import ChatMessageFile


class ChatMessageFileMapper(BaseMapper[ChatMessageFile]):
    model = ChatMessageFile
    pk_name = "id"

    async def list_by_message_id(self, message_id: str) -> List[ChatMessageFile]:
        result = await self.db.execute(
            select(ChatMessageFile).where(ChatMessageFile.message_id == message_id)
        )
        return result.scalars().all()

    async def list_by_file_id(self, file_id: int) -> List[ChatMessageFile]:
        result = await self.db.execute(
            select(ChatMessageFile).where(ChatMessageFile.file_id == file_id)
        )
        return result.scalars().all()

    async def get_by_message_and_file(
        self, message_id: str, file_id: int
    ) -> Optional[ChatMessageFile]:
        result = await self.db.execute(
            select(ChatMessageFile).where(
                ChatMessageFile.message_id == message_id,
                ChatMessageFile.file_id == file_id,
            )
        )
        return result.scalars().first()

    async def bulk_create_for_message(
        self, message_id: str, file_ids: List[int]
    ) -> List[ChatMessageFile]:
        """给指定 message_id 批量关联 file_id 列表（跳过已存在的）"""
        existing = await self.list_by_message_id(message_id)
        existing_ids = {r.file_id for r in existing}
        new_ids = [fid for fid in file_ids if fid not in existing_ids]
        if not new_ids:
            return []
        return await self.bulk_create_from_dicts(
            [{"message_id": message_id, "file_id": fid} for fid in new_ids]
        )

    async def delete_by_message_id(self, message_id: str) -> int:
        result = await self.db.execute(
            delete(ChatMessageFile).where(ChatMessageFile.message_id == message_id)
        )
        return result.rowcount

    async def delete_by_message_and_file(self, message_id: str, file_id: int) -> bool:
        result = await self.db.execute(
            delete(ChatMessageFile).where(
                ChatMessageFile.message_id == message_id,
                ChatMessageFile.file_id == file_id,
            )
        )
        return result.rowcount > 0

    async def get_file_ids_by_message_id(self, message_id: str) -> List[int]:
        records = await self.list_by_message_id(message_id)
        return [r.file_id for r in records]

    async def get_file_ids_by_message_ids(
            self, message_ids: List[str]
    ) -> Dict[str, List[int]]:
        """
        批量查询 message_id -> [file_id] 映射。
        1 次 SQL，无 N+1。
        """
        if not message_ids:
            return {}
        stmt = select(ChatMessageFile).where(
            ChatMessageFile.message_id.in_(message_ids)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        mapping: Dict[str, List[int]] = {}
        for row in rows:
            mapping.setdefault(row.message_id, []).append(row.file_id)
        return mapping