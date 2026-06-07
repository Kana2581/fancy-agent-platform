from typing import List

from sqlalchemy import delete, select

from app.mappers.base_mapper import BaseMapper
from app.models.skill_file import SkillFile


class SkillFileMapper(BaseMapper[SkillFile]):
    model = SkillFile

    async def list_by_skill(self, skill_id: int) -> List[SkillFile]:
        result = await self.db.execute(
            select(SkillFile).where(SkillFile.skill_id == skill_id).order_by(SkillFile.path.asc())
        )
        return list(result.scalars().all())

    async def replace_for_skill(self, skill_id: int, files: List[dict]) -> List[SkillFile]:
        """整组替换某 skill 的文件：先删旧、再插新。files: [{path, content, size}]。"""
        await self.db.execute(delete(SkillFile).where(SkillFile.skill_id == skill_id))
        if not files:
            return []
        objs = [SkillFile(skill_id=skill_id, **f) for f in files]
        self.db.add_all(objs)
        await self.db.flush()
        return objs
