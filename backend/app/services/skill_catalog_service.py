"""Filesystem-first Skill discovery.

Skill packages are intentionally not persisted in MySQL.  This module scans the
system package tree and the current user's package tree on demand and returns a
request-local catalog used by both prompts and sandbox mounts.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import yaml

from app.core.config import settings
from app.services.skill_package_service import FRONTMATTER_RE


@dataclass(frozen=True)
class SkillCatalogEntry:
    scope: str
    user_id: Optional[int]
    package_path: str
    name: str
    description: str
    status: str
    error: Optional[str]
    files: tuple[dict, ...]
    content_hash: Optional[str] = None

    @property
    def mount_path(self) -> str:
        return f"/skills/{self.scope}/{self.package_path}"

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


def _root(scope: str, user_id: Optional[int]) -> Path:
    if scope == "system":
        return Path(settings.SYSTEM_SKILLS_DIR).expanduser().resolve()
    if scope == "user" and user_id is not None:
        return (Path(settings.USER_SKILLS_DIR) / str(user_id)).expanduser().resolve()
    raise ValueError("Skill scope/user_id combination is invalid")


def _safe_child(root: Path, package_path: str) -> Path:
    candidate = Path((package_path or "").replace("\\", "/"))
    if (
        not package_path
        or candidate.is_absolute()
        or len(candidate.parts) != 1
        or candidate.name in {".", ".."}
    ):
        raise ValueError("Skill package path is invalid")
    target = (root / candidate).resolve()
    if target == root or root not in target.parents:
        raise ValueError("Skill package path escapes its root")
    if (root / candidate).is_symlink() or not target.is_dir():
        raise ValueError("Skill package is missing or is a symlink")
    return target


def _iter_package_dirs(root: Path) -> Iterable[tuple[str, Path]]:
    if not root.exists():
        return
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if entry.is_dir() and not entry.is_symlink():
            yield entry.name, entry


def _read_frontmatter(skill_file: Path) -> tuple[str, str, str]:
    raw = skill_file.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError("SKILL.md must start with YAML frontmatter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()
    if not name or not description:
        raise ValueError("SKILL.md requires name and description")
    return name, description, raw


def _scan_files(package: Path) -> tuple[tuple[dict, ...], str]:
    files: list[dict] = []
    digest = hashlib.sha256()
    total = 0
    for entry in sorted(package.rglob("*"), key=lambda item: item.as_posix()):
        if entry.is_symlink():
            relative = entry.relative_to(package).as_posix()
            raise ValueError(f"Skill package contains a symlink: {relative}")
        if not entry.is_file():
            continue
        relative = entry.relative_to(package).as_posix()
        size = entry.stat().st_size
        if size > settings.SKILL_MAX_FILE_BYTES:
            raise ValueError(f"Skill file exceeds limit: {relative}")
        total += size
        if len(files) >= settings.SKILL_MAX_FILES or total > settings.SKILL_MAX_PACKAGE_BYTES:
            raise ValueError("Skill package exceeds file or size limits")
        digest.update(relative.encode("utf-8"))
        digest.update(entry.read_bytes())
        files.append({"path": relative, "size": size, "type": "file"})
    return tuple(files), digest.hexdigest()


def scan_skill_package(scope: str, user_id: Optional[int], package_path: str) -> SkillCatalogEntry:
    root = _root(scope, user_id)
    package = _safe_child(root, package_path)
    try:
        name, description, _ = _read_frontmatter(package / "SKILL.md")
        files, content_hash = _scan_files(package)
        return SkillCatalogEntry(
            scope=scope,
            user_id=user_id,
            package_path=package_path,
            name=name,
            description=description,
            status="ready",
            error=None,
            files=files,
            content_hash=content_hash,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return SkillCatalogEntry(
            scope=scope,
            user_id=user_id,
            package_path=package_path,
            name=package_path,
            description="",
            status="invalid",
            error=str(exc),
            files=(),
        )


def scan_skill_catalog(user_id: int, scope: str = "all", include_invalid: bool = True) -> list[SkillCatalogEntry]:
    scopes = ["system", "user"] if scope == "all" else [scope]
    result: list[SkillCatalogEntry] = []
    for current_scope in scopes:
        current_root = _root(current_scope, user_id if current_scope == "user" else None)
        for package_path, package in _iter_package_dirs(current_root):
            entry = scan_skill_package(
                current_scope,
                user_id if current_scope == "user" else None,
                package_path,
            )
            if include_invalid or entry.is_ready:
                result.append(entry)
    return result


def resolve_skill_file(scope: str, user_id: int, package_path: str, file_path: str) -> Path:
    root = _root(scope, user_id if scope == "user" else None)
    package = _safe_child(root, package_path)
    relative = Path((file_path or "").replace("\\", "/"))
    if not file_path or relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Skill file path is invalid")
    target = (package / relative).resolve()
    if package not in target.parents or target.is_symlink() or not target.is_file():
        raise ValueError("Skill file does not exist or escapes its package")
    return target


def skill_root_mounts(user_id: int) -> list[dict]:
    """Return backend-owned root mounts for a sandbox request."""
    user_root = _root("user", user_id)
    user_root.mkdir(parents=True, exist_ok=True)
    return [
        {"scope": "system", "user_id": None, "read_only": True},
        {"scope": "user", "user_id": user_id, "read_only": False},
    ]


def serialize_skill(entry: SkillCatalogEntry) -> dict:
    return {
        "scope": entry.scope,
        "package_path": entry.package_path,
        "name": entry.name,
        "description": entry.description,
        "package_status": entry.status,
        "error": entry.error,
        "content_hash": entry.content_hash,
        "files": list(entry.files),
        "mount_path": entry.mount_path,
    }
