from typing import List, Optional

from sqlalchemy import select, update

from app.mappers.base_mapper import BaseMapper
from app.models.message_approval import MessageApproval


class MessageApprovalMapper(BaseMapper[MessageApproval]):
    model = MessageApproval
    pk_name = "message_id"

    async def get_by_message_id(self, message_id: str) -> Optional[MessageApproval]:
        stmt = select(MessageApproval).where(MessageApproval.message_id == message_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_by_message_ids(
        self, message_ids: List[str]
    ) -> Optional[MessageApproval]:
        """Return the first pending approval found among the given message IDs."""
        if not message_ids:
            return None
        stmt = (
            select(MessageApproval)
            .where(
                MessageApproval.message_id.in_(message_ids),
                MessageApproval.status == "pending",
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_message_ids(
        self, message_ids: List[str]
    ) -> List[MessageApproval]:
        """Return all approvals for the given message IDs."""
        if not message_ids:
            return []
        stmt = select(MessageApproval).where(
            MessageApproval.message_id.in_(message_ids)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, message_id: str, status: str) -> None:
        stmt = (
            update(MessageApproval)
            .where(MessageApproval.message_id == message_id)
            .values(status=status)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def create_pending(self, message_id: str) -> MessageApproval:
        return await self.create_from_dict({"message_id": message_id, "status": "pending"})
