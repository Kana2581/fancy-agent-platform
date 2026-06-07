from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.skill_file_mapper import SkillFileMapper
from app.mappers.skill_mapper import SkillMapper
from app.models.skill import Skill, SKILL_SCOPE_SYSTEM, SKILL_SCOPE_USER, SKILL_SCOPE_SESSION
from app.models.skill_file import SkillFile
from app.schemas.skill_schema import SkillUpdate


# 技能文件 caps（作者侧限死，物化时无需再查配额）
MAX_SKILL_FILE_BYTES = 64 * 1024
MAX_SKILL_FILES = 20
MAX_SKILL_TOTAL_BYTES = 256 * 1024


def validate_skill_files(files: Optional[list]) -> List[dict]:
    """校验并规范化技能文件列表（path 安全 + caps）。

    files 元素可为 SkillFileIn / dict / 任何带 .path/.content 的对象。
    返回 [{path, content, size}]；违规抛 ValueError。
    """
    if not files:
        return []
    if len(files) > MAX_SKILL_FILES:
        raise ValueError(f"技能文件数超限：> {MAX_SKILL_FILES}")

    seen: set = set()
    total = 0
    out: List[dict] = []
    for f in files:
        path = getattr(f, "path", None) if not isinstance(f, dict) else f.get("path")
        content = getattr(f, "content", None) if not isinstance(f, dict) else f.get("content")
        path = (path or "").strip().replace("\\", "/").lstrip("/")
        content = content or ""

        if not path:
            raise ValueError("技能文件 path 不能为空")
        if len(path) >= 2 and path[1] == ":":
            raise ValueError(f"技能文件 path 不允许盘符/绝对路径：{path}")
        parts = path.split("/")
        if any(seg in ("", ".", "..") for seg in parts):
            raise ValueError(f"技能文件 path 非法（含 .. 或空段）：{path}")
        if path in seen:
            raise ValueError(f"技能文件 path 重复：{path}")
        seen.add(path)

        size = len(content.encode("utf-8"))
        if size > MAX_SKILL_FILE_BYTES:
            raise ValueError(f"技能文件超限：{path} {size} 字节 > {MAX_SKILL_FILE_BYTES}")
        total += size
        if total > MAX_SKILL_TOTAL_BYTES:
            raise ValueError(f"技能文件合计超限：> {MAX_SKILL_TOTAL_BYTES} 字节")

        out.append({"path": path, "content": content, "size": size})
    return out


class SkillService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = SkillMapper(db)
        self.file_mapper = SkillFileMapper(db)

    async def create_skill(self, data: dict) -> Skill:
        # 先校验文件，避免建了 skill 行又因文件失败
        files = validate_skill_files(data.pop("files", None))

        # 默认 scope=user，确保旧调用方不破
        data.setdefault("scope", SKILL_SCOPE_USER)
        if data["scope"] != SKILL_SCOPE_SESSION:
            # 非 session 行用空串占位，配合 uq_skill_scope_name 在 MySQL 下生效
            data["session_id"] = ""
        else:
            data["session_id"] = data.get("session_id") or ""

        # 应用层兜底查重：MySQL 历史数据里可能存在 session_id=NULL 的行，
        # 让唯一索引无法拦住同名重复；这里在 insert 前先按 (user_id, scope, name) 查一次。
        existing = await self.mapper.get_owned_by_name(
            user_id=data["user_id"],
            scope=data["scope"],
            name=data["name"],
            session_id=data["session_id"] if data["scope"] == SKILL_SCOPE_SESSION else None,
        )
        if existing:
            raise ValueError(f"同名技能已存在: {data['name']}")

        res = await self.mapper.create_from_dict(data)
        if files:
            await self.file_mapper.replace_for_skill(res.id, files)
        await self.db.commit()
        await self.db.refresh(res)
        return res

    async def upsert_system_skill(self, data: dict) -> Skill:
        """system skills 用 user_id=0 + scope=system，按 name 幂等。"""
        files = validate_skill_files(data.pop("files", None))
        existing = await self.mapper.get_system_by_name(data["name"])
        if existing:
            payload = {k: v for k, v in data.items() if k in ("content", "description", "category")}
            res = await self.mapper.update_by_id(existing.id, payload)
            await self.file_mapper.replace_for_skill(existing.id, files)
            await self.db.commit()
            await self.db.refresh(res)
            return res
        data.update({"user_id": 0, "scope": SKILL_SCOPE_SYSTEM, "session_id": ""})
        res = await self.mapper.create_from_dict(data)
        if files:
            await self.file_mapper.replace_for_skill(res.id, files)
        await self.db.commit()
        await self.db.refresh(res)
        return res

    async def get_skill(self, skill_id: int) -> Optional[Skill]:
        return await self.mapper.get_by_id(skill_id)

    async def get_files(self, skill_id: int) -> List[SkillFile]:
        return await self.file_mapper.list_by_skill(skill_id)

    async def list_by_user(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[Skill]:
        filters = {"user_id": user_id}
        if category:
            filters["category"] = category
        if scope:
            filters["scope"] = scope
        return await self.mapper.list_by_filters(filters=filters, offset=offset, limit=limit)

    async def list_layered(
        self,
        user_id: int,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Skill]:
        return await self.mapper.list_layered(user_id, session_id, category)

    async def update_skill(self, skill_id: int, data: SkillUpdate) -> Optional[Skill]:
        payload = data.model_dump(exclude_unset=True)
        files_set = "files" in payload
        files = validate_skill_files(payload.pop("files", None)) if files_set else []

        res: Optional[Skill]
        if payload:
            res = await self.mapper.update_by_id(skill_id, payload)
        else:
            res = await self.mapper.get_by_id(skill_id)
        if res is None:
            return None
        if files_set:
            await self.file_mapper.replace_for_skill(skill_id, files)
        await self.db.commit()
        await self.db.refresh(res)
        return res

    async def delete_skill(self, skill_id: int) -> bool:
        res = await self.mapper.delete_by_id(skill_id)
        await self.db.commit()
        return res

    async def delete_session_skills(self, session_id: str) -> int:
        count = await self.mapper.delete_session_skills(session_id)
        await self.db.commit()
        return count
