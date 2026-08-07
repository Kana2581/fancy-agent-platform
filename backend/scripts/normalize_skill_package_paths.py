"""Normalize legacy numeric user Skill directories to their package names.

User Skill storage is ``USER_SKILLS_DIR/<user_id>/<package_path>`` and the
package path is the directory name. Older exports used numeric Skill IDs,
which made the runtime mount paths ambiguous. This migration is idempotent.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import yaml

from app.core.config import settings


_SAFE_NAME = re.compile(r"^[^/\\]+$")


def _package_name(package: Path) -> str | None:
    skill_file = package / "SKILL.md"
    if not skill_file.is_file():
        return None
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    _, frontmatter, _ = text.split("---", 2)
    data = yaml.safe_load(frontmatter)
    name = str(data.get("name", "")).strip() if isinstance(data, dict) else ""
    if not name or name in {".", ".."} or not _SAFE_NAME.fullmatch(name):
        return None
    return name


def normalize(root: Path) -> list[tuple[str, str]]:
    renamed: list[tuple[str, str]] = []
    if not root.is_dir():
        return renamed
    for user_root in sorted(root.iterdir(), key=lambda item: item.name):
        if not user_root.is_dir() or user_root.is_symlink():
            continue
        for package in sorted(user_root.iterdir(), key=lambda item: item.name):
            if not package.is_dir() or package.is_symlink() or not package.name.isdigit():
                continue
            name = _package_name(package)
            if not name or name == package.name:
                continue
            target = user_root / name
            if target.exists():
                raise RuntimeError(f"目标 Skill 目录已存在，未迁移: {target}")
            package.rename(target)
            renamed.append((str(package), str(target)))
    return renamed


async def main() -> None:
    for source, target in normalize(Path(settings.USER_SKILLS_DIR).expanduser().resolve()):
        print(f"renamed {source} -> {target}")


if __name__ == "__main__":
    asyncio.run(main())
