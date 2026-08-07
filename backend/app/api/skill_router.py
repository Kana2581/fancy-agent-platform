import asyncio
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps.user import get_current_user
from app.schemas.skill_schema import SkillFileContentOut, SkillOut, SkillTreeNode
from app.services.skill_catalog_service import (
    resolve_skill_file,
    scan_skill_catalog,
    scan_skill_package,
    serialize_skill,
)


router = APIRouter(prefix="/skills", tags=["Skills"])


def _serialize_skill(skill) -> SkillOut:
    """Compatibility adapter for legacy tests and one-time migrations."""
    root = None
    entry = scan_skill_package(
        getattr(skill, "source_type", "user"),
        getattr(skill, "user_id", None),
        getattr(skill, "package_path", ""),
    )
    payload = serialize_skill(entry)
    try:
        from app.services.skill_catalog_service import _root
        root = _root(entry.scope, entry.user_id)
        payload["files"] = [
            item for item in payload["files"]
            if _is_text_file(root / entry.package_path / item["path"])
        ]
    except (OSError, UnicodeDecodeError, ValueError):
        payload["files"] = []
    return SkillOut.model_validate(payload)


def _is_text_file(path) -> bool:
    try:
        path.read_text(encoding="utf-8")
        return True
    except (OSError, UnicodeDecodeError):
        return False


@router.get("", response_model=List[SkillOut])
async def list_skills(
    scope: Literal["all", "user", "system"] = Query("all"),
    user_id: int = Depends(get_current_user),
):
    entries = await asyncio.to_thread(scan_skill_catalog, user_id, scope, True)
    return [serialize_skill(entry) for entry in entries]


@router.get("/tree", response_model=List[SkillTreeNode])
async def list_skill_tree(
    scope: Literal["user", "system"],
    package_path: str,
    user_id: int = Depends(get_current_user),
):
    try:
        entry = await asyncio.to_thread(
            scan_skill_package,
            scope,
            user_id if scope == "user" else None,
            package_path,
        )
        if entry.status != "ready":
            raise ValueError(entry.error or "Skill package is invalid")
        return [
            SkillTreeNode(
                name=item["path"].rsplit("/", 1)[-1],
                path=item["path"],
                type=item.get("type", "file"),
                size=item.get("size"),
            )
            for item in entry.files
        ]
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/file", response_model=SkillFileContentOut)
async def read_skill_file(
    scope: Literal["user", "system"],
    package_path: str,
    path: str,
    user_id: int = Depends(get_current_user),
):
    try:
        target = await asyncio.to_thread(
            resolve_skill_file, scope, user_id, package_path, path
        )
        size = target.stat().st_size
        if size > 512 * 1024:
            raise ValueError("Skill file is too large for preview")
        content = await asyncio.to_thread(target.read_text, encoding="utf-8")
        return SkillFileContentOut(
            scope=scope,
            package_path=package_path,
            path=path,
            content=content,
            size=size,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
