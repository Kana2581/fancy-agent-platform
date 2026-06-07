from typing import Optional, List, Dict

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.chat_file_content import ChatFileContent


class ChatFileContentMapper(BaseMapper[ChatFileContent]):
    model = ChatFileContent

    async def get_by_file_id(self, file_id: int) -> Optional[ChatFileContent]:
        result = await self.db.execute(
            select(ChatFileContent).where(ChatFileContent.file_id == file_id)
        )
        return result.scalars().first()

    async def get_by_file_ids(self, file_ids: List[int]) -> Dict[int, ChatFileContent]:
        """
        批量查询 file_id -> ChatFileContent 映射。
        1 次 SQL，未解析的 file_id 不出现在结果中。
        """
        if not file_ids:
            return {}
        stmt = select(ChatFileContent).where(ChatFileContent.file_id.in_(file_ids))
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return {row.file_id: row for row in rows}