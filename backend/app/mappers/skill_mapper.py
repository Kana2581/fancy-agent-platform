from typing import List, Optional

from sqlalchemy import select, or_, and_

from app.mappers.base_mapper import BaseMapper
from app.models.skill import Skill, SKILL_SCOPE_SYSTEM, SKILL_SCOPE_USER


class SkillMapper(BaseMapper):
    model = Skill

    async def get_by_name(
        self,
        user_id: int,
        name: str,
    ) -> Optional[Skill]:
        """按 system < user 优先级解析同名 Skill。"""
        conditions = [
            and_(Skill.scope == SKILL_SCOPE_SYSTEM, Skill.name == name),
            and_(Skill.scope == SKILL_SCOPE_USER, Skill.user_id == user_id, Skill.name == name),
        ]
        result = await self.db.execute(select(Skill).where(or_(*conditions)))
        rows = result.scalars().all()
        if not rows:
            return None
        priority = {SKILL_SCOPE_USER: 2, SKILL_SCOPE_SYSTEM: 1}
        rows.sort(key=lambda r: priority.get(r.scope, 0), reverse=True)
        return rows[0]

    async def list_layered(
        self,
        user_id: int,
        category: Optional[str] = None,
    ) -> List[Skill]:
        """合并 system/user Skills；同名时由调用方处理覆盖逻辑。"""
        conditions = [
            Skill.scope == SKILL_SCOPE_SYSTEM,
            and_(Skill.scope == SKILL_SCOPE_USER, Skill.user_id == user_id),
        ]
        stmt = select(Skill).where(or_(*conditions))
        if category:
            stmt = stmt.where(Skill.category == category)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_system_by_name(self, name: str) -> Optional[Skill]:
        # 用 order_by + first 而不是 scalar_one_or_none：
        # 历史 DB 可能因 session_id=NULL 唯一约束失效而残留重复行，避免抛异常。
        result = await self.db.execute(
            select(Skill)
            .where(Skill.scope == SKILL_SCOPE_SYSTEM, Skill.name == name)
            .order_by(Skill.id.asc())
            .limit(1)
        )
        return result.scalars().first()

    async def list_system_skills(self) -> List[Skill]:
        result = await self.db.execute(
            select(Skill).where(Skill.scope == SKILL_SCOPE_SYSTEM)
        )
        return list(result.scalars().all())

    async def get_owned_by_name(
        self,
        user_id: int,
        scope: str,
        name: str,
    ) -> Optional[Skill]:
        """按 (user_id, scope, name) 查询单条；用于 insert 前查重。"""
        stmt = select(Skill).where(
            Skill.user_id == user_id,
            Skill.scope == scope,
            Skill.name == name,
        )
        result = await self.db.execute(stmt.order_by(Skill.id.asc()).limit(1))
        return result.scalars().first()
