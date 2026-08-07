from pathlib import Path
import shutil
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.skill_file_mapper import SkillFileMapper
from app.mappers.skill_mapper import SkillMapper
from app.models.skill import Skill, SKILL_SCOPE_SYSTEM, SKILL_SCOPE_USER
from app.models.skill_file import SkillFile
from app.schemas.skill_schema import SkillUpdate
from app.services.skill_package_service import (
    normalize_skill_name,
    now_iso,
    package_dir,
    scan_package,
    write_package,
)


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
        data["name"] = normalize_skill_name(data.get("name", ""))

        # session Skill 已废弃；保留显式拒绝，避免旧调用方静默创建错误 scope。
        requested_scope = data.pop("scope", None)
        data.pop("session_id", None)
        if requested_scope not in (None, SKILL_SCOPE_USER):
            raise ValueError("仅支持创建 user Skill")
        data["scope"] = SKILL_SCOPE_USER

        # 应用层兜底查重：MySQL 历史数据里可能存在 session_id=NULL 的行，
        # 让唯一索引无法拦住同名重复；这里在 insert 前先按 (user_id, scope, name) 查一次。
        existing = await self.mapper.get_owned_by_name(
            user_id=data["user_id"],
            scope=data["scope"],
            name=data["name"],
        )
        if existing:
            raise ValueError(f"同名技能已存在: {data['name']}")

        source_type = "user"
        data.update({"source_type": source_type, "package_status": "ready"})
        res = await self.mapper.create_from_dict(data)
        package_path = normalize_skill_name(res.name)
        try:
            metadata = write_package(
                source_type, int(data["user_id"]), package_path,
                name=res.name, description=res.description, content=res.content,
                files=files,
            )
        except Exception:
            await self.db.delete(res)
            await self.db.commit()
            raise
        res.package_path = package_path
        res.content_hash = metadata.content_hash
        res.last_scanned_at = now_iso()
        if files:
            await self.file_mapper.replace_for_skill(res.id, files)
        await self.db.commit()
        await self.db.refresh(res)
        return res

    async def upsert_system_skill(self, data: dict) -> Skill:
        """system skills 用 user_id=0 + scope=system，按 name 幂等。"""
        files = validate_skill_files(data.pop("files", None))
        data["name"] = normalize_skill_name(data.get("name", ""))
        existing = await self.mapper.get_system_by_name(data["name"])
        if existing:
            payload = {k: v for k, v in data.items() if k in ("content", "description", "category")}
            res = await self.mapper.update_by_id(existing.id, payload)
            await self.file_mapper.replace_for_skill(existing.id, files)
            await self.db.commit()
            await self.db.refresh(res)
            return res
        data.update({
            "user_id": 0, "scope": SKILL_SCOPE_SYSTEM, "source_type": "system",
            "package_path": data["name"], "package_status": "ready",
        })
        res = await self.mapper.create_from_dict(data)
        if files:
            await self.file_mapper.replace_for_skill(res.id, files)
        await self.db.commit()
        await self.db.refresh(res)
        return res

    async def scan_system_packages(self) -> int:
        """Index valid ``<root>/*/SKILL.md`` packages at startup."""
        root = Path(__import__("app.core.config", fromlist=["settings"]).settings.SYSTEM_SKILLS_DIR)
        count = 0
        valid_package_paths: set[str] = set()
        if root.exists() and root.is_dir():
            for package in sorted(root.iterdir()):
                if not package.is_dir() or package.is_symlink() or not (package / "SKILL.md").is_file():
                    continue
                package_path = package.name
                try:
                    metadata = scan_package("system", None, package_path)
                except (OSError, UnicodeDecodeError, ValueError):
                    continue
                existing = await self.mapper.get_system_by_name(metadata.name)
                payload = {
                    "user_id": 0, "name": metadata.name,
                    "description": metadata.description,
                    "content": (package / "SKILL.md").read_text(encoding="utf-8"),
                    "scope": SKILL_SCOPE_SYSTEM,
                    "source_type": "system", "package_path": package_path,
                    "package_status": "ready", "content_hash": metadata.content_hash,
                    "last_scanned_at": now_iso(),
                }
                if existing:
                    await self.mapper.update_by_id(existing.id, payload)
                else:
                    await self.mapper.create_from_dict(payload)
                valid_package_paths.add(package_path)
                count += 1

        for skill in await self.mapper.list_system_skills():
            if skill.source_type == "system" and skill.package_path not in valid_package_paths:
                await self.mapper.update_by_id(skill.id, {
                    "package_status": "invalid",
                    "last_scanned_at": now_iso(),
                })
        await self.db.commit()
        return count

    async def purge_legacy_session_skills(self) -> int:
        """Remove obsolete session Skill rows and their packages."""
        result = await self.db.execute(select(Skill).where(Skill.scope == "session"))
        skills = list(result.scalars().all())
        for skill in skills:
            if skill.package_path:
                try:
                    # Legacy session packages used the same per-user root as user packages.
                    target = package_dir("user", int(skill.user_id), skill.package_path)
                except (OSError, ValueError):
                    target = None
                if target and target.exists():
                    shutil.rmtree(target, ignore_errors=True)
            await self.db.delete(skill)
        if skills:
            await self.db.commit()
        return len(skills)

    async def migrate_legacy_packages(self) -> int:
        """Materialize old DB-backed user Skills once into the user volume."""
        rows = await self.mapper.list_all()
        migrated = 0
        for skill in rows:
            if skill.scope == SKILL_SCOPE_SYSTEM or skill.package_path:
                continue
            files = [
                {"path": item.path, "content": item.content}
                for item in await self.file_mapper.list_by_skill(skill.id)
            ]
            source_type = "user"
            try:
                metadata = write_package(
                    source_type, int(skill.user_id), normalize_skill_name(skill.name),
                    name=skill.name, description=skill.description,
                    content=skill.content, files=files,
                )
            except (OSError, ValueError):
                skill.package_status = "invalid"
                continue
            skill.source_type = source_type
            skill.package_path = normalize_skill_name(skill.name)
            skill.package_status = "ready"
            skill.content_hash = metadata.content_hash
            skill.last_scanned_at = now_iso()
            migrated += 1
        if migrated:
            await self.db.commit()
        return migrated

    async def get_skill(self, skill_id: int) -> Optional[Skill]:
        return await self.mapper.get_by_id(skill_id)

    async def get_files(self, skill_id: int) -> List[SkillFile]:
        return await self.file_mapper.list_by_skill(skill_id)

    async def reindex_package(self, skill_id: int) -> Optional[Skill]:
        """Refresh DB metadata after a sandbox changed SKILL.md or its package."""
        skill = await self.mapper.get_by_id(skill_id)
        if not skill or skill.source_type not in {"user", "system"} or not skill.package_path:
            return skill
        try:
            metadata = scan_package(skill.source_type, int(skill.user_id), skill.package_path)
            skill_file = package_dir(skill.source_type, int(skill.user_id), skill.package_path) / "SKILL.md"
            payload = {
                "name": metadata.name,
                "description": metadata.description,
                "content": skill_file.read_text(encoding="utf-8"),
                "package_status": "ready",
                "content_hash": metadata.content_hash,
                "last_scanned_at": now_iso(),
            }
        except (OSError, ValueError):
            payload = {"package_status": "invalid", "last_scanned_at": now_iso()}
        await self.mapper.update_by_id(skill_id, payload)
        await self.db.commit()
        return await self.mapper.get_by_id(skill_id)

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
        category: Optional[str] = None,
    ) -> List[Skill]:
        return await self.mapper.list_layered(user_id, category)

    async def update_skill(self, skill_id: int, data: SkillUpdate) -> Optional[Skill]:
        payload = data.model_dump(exclude_unset=True)
        files_set = "files" in payload
        files = validate_skill_files(payload.pop("files", None)) if files_set else []

        res: Optional[Skill]
        res = await self.mapper.get_by_id(skill_id)
        if res is None:
            return None
        if res.scope == SKILL_SCOPE_SYSTEM:
            raise ValueError("系统级技能不可修改")
        new_name = normalize_skill_name(payload.get("name", res.name))
        new_description = payload.get("description", res.description)
        new_content = payload.get("content", res.content)
        if payload or files_set:
            old_package_path = res.package_path
            package_path = normalize_skill_name(new_name)
            renamed = bool(old_package_path and old_package_path != package_path and res.source_type == "user")
            moved = False
            old_target = package_dir("user", int(res.user_id), old_package_path) if renamed else None
            new_target = package_dir("user", int(res.user_id), package_path)
            if renamed and new_target.exists():
                raise ValueError(f"同名技能目录已存在: {package_path}")
            if renamed and old_target is not None and old_target.exists():
                import os
                os.replace(old_target, new_target)
                moved = True
            if files_set:
                package_files = files
            elif res.package_path and res.source_type == "user":
                try:
                    package_root = package_dir(res.source_type, int(res.user_id), package_path)
                    package_files = [
                        {"path": item["path"], "content": (package_root / item["path"]).read_text(encoding="utf-8")}
                        for item in scan_package(res.source_type, int(res.user_id), package_path).files
                        if item["path"] != "SKILL.md"
                    ]
                except (OSError, UnicodeDecodeError, ValueError):
                    package_files = []
            else:
                package_files = [
                    {"path": f.path, "content": f.content}
                    for f in await self.file_mapper.list_by_skill(skill_id)
                ]
            try:
                metadata = write_package(
                    "user", int(res.user_id), package_path,
                    name=new_name, description=new_description, content=new_content,
                    files=package_files,
                )
            except Exception:
                if moved and new_target.exists() and old_target is not None and not old_target.exists():
                    import os
                    os.replace(new_target, old_target)
                raise
            if renamed and old_target is not None and old_target.exists():
                shutil.rmtree(old_target)
            payload.update({
                "name": metadata.name, "description": metadata.description,
                "content": new_content, "package_path": package_path,
                "source_type": "user",
                "package_status": "ready", "content_hash": metadata.content_hash,
                "last_scanned_at": now_iso(),
            })
        if payload:
            res = await self.mapper.update_by_id(skill_id, payload)
        if files_set:
            await self.file_mapper.replace_for_skill(skill_id, files)
        await self.db.commit()
        await self.db.refresh(res)
        return res

    async def delete_skill(self, skill_id: int) -> bool:
        existing = await self.mapper.get_by_id(skill_id)
        if existing and existing.scope != SKILL_SCOPE_SYSTEM and existing.package_path:
            target = package_dir("user", int(existing.user_id), existing.package_path)
            if target.exists():
                import shutil
                shutil.rmtree(target)
        res = await self.mapper.delete_by_id(skill_id)
        await self.db.commit()
        return res
