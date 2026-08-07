"""Shared filesystem validation for Skill packages.

Package files are the source of truth.  Database-backed helpers remain in this
module only for the one-time legacy export script and older unit tests; runtime
discovery uses ``skill_catalog_service`` instead.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import yaml

from app.core.config import settings


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MAX_OUTPUT = 12_000


def normalize_skill_name(name: str) -> str:
    """Return the filesystem-safe, single-component Skill name."""
    value = (name or "").strip()
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError("Skill name/path must be a non-empty single directory name")
    return value


@dataclass(frozen=True)
class PackageMetadata:
    name: str
    description: str
    package_path: str
    files: list[dict]
    content_hash: str


def _root(source_type: str, user_id: Optional[int] = None) -> Path:
    if source_type == "system":
        return Path(settings.SYSTEM_SKILLS_DIR).expanduser().resolve()
    if source_type == "user":
        if user_id is None:
            raise ValueError("user_id is required for user Skill packages")
        return (Path(settings.USER_SKILLS_DIR) / str(user_id)).resolve()
    raise ValueError(f"Unsupported Skill source: {source_type}")


def package_dir(source_type: str, user_id: Optional[int], package_path: str) -> Path:
    """Resolve a stored relative package path and reject traversal/symlinks."""
    package_path = normalize_skill_name(package_path)
    root = _root(source_type, user_id)
    candidate = Path(package_path.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts or len(candidate.parts) != 1:
        raise ValueError("Skill package path is invalid")
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("Skill package path escapes its root")
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Skill package symlinks are not allowed")
    return resolved


def _parse_frontmatter(skill_file: Path) -> tuple[str, str]:
    text = skill_file.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{skill_file} must start with YAML frontmatter")
    raw = yaml.safe_load(match.group(1))
    if not isinstance(raw, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    name = str(raw.get("name", "")).strip()
    description = str(raw.get("description", "")).strip()
    if not name or not description:
        raise ValueError("SKILL.md requires name and description")
    return name, description


def _iter_files(root: Path) -> Iterable[Path]:
    for entry in sorted(root.rglob("*")):
        if entry.is_symlink() or not entry.is_file():
            continue
        yield entry


def scan_package(source_type: str, user_id: Optional[int], package_path: str) -> PackageMetadata:
    root = package_dir(source_type, user_id, package_path)
    skill_file = root / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError("Skill package is missing SKILL.md")
    name, description = _parse_frontmatter(skill_file)
    files: list[dict] = []
    digest = hashlib.sha256()
    total = 0
    for file_path in _iter_files(root):
        relative = file_path.relative_to(root).as_posix()
        size = file_path.stat().st_size
        if size > settings.SKILL_MAX_FILE_BYTES:
            raise ValueError(f"Skill file exceeds limit: {relative}")
        total += size
        if len(files) >= settings.SKILL_MAX_FILES or total > settings.SKILL_MAX_PACKAGE_BYTES:
            raise ValueError("Skill package exceeds file or size limits")
        digest.update(relative.encode("utf-8"))
        digest.update(file_path.read_bytes())
        files.append({"path": relative, "size": size})
    return PackageMetadata(name, description, package_path, files, digest.hexdigest())


def write_package(
    source_type: str,
    user_id: int,
    package_path: str,
    *,
    name: str,
    description: Optional[str],
    content: str,
    files: list[dict],
) -> PackageMetadata:
    """Atomically replace a user package from API payload data."""
    if source_type == "system":
        raise ValueError("System Skill packages are read-only")
    package_path = normalize_skill_name(package_path)
    target = package_dir(source_type, user_id, package_path)
    root = target.parent
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="skill-", dir=str(root)))
    try:
        frontmatter = {
            "name": name,
            "description": description or name,
        }
        body = content.strip() + "\n"
        (stage / "SKILL.md").write_text(
            "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n" + body,
            encoding="utf-8",
        )
        for item in files:
            relative = str(item["path"]).replace("\\", "/")
            relative_path = Path(relative)
            if (not relative or relative_path.is_absolute() or ".." in relative_path.parts
                    or relative_path.as_posix() == "SKILL.md"):
                raise ValueError("Skill file path is invalid")
            output = stage / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(str(item.get("content", "")), encoding="utf-8")
        backup = target.with_name(target.name + ".previous")
        if target.exists():
            if source_type == "system":
                raise ValueError("System Skill packages are read-only")
            if backup.exists():
                shutil.rmtree(backup)
            os.replace(target, backup)
        os.replace(stage, target)
        if backup.exists():
            shutil.rmtree(backup)
        return scan_package(source_type, user_id, package_path)
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
