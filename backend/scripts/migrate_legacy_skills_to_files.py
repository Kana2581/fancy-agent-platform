"""Materialize legacy database Skills before dropping their tables.

Run this script once against an existing deployment, before applying
``db_init/02_remove_legacy_skill_tables.sql``.
"""

import asyncio
from pathlib import Path

from app.core.database import async_session_factory
from app.services.skill_service import SkillService
from normalize_skill_package_paths import normalize
from app.core.config import settings


async def main() -> None:
    for source, target in normalize(Path(settings.USER_SKILLS_DIR).expanduser().resolve()):
        print(f"renamed {source} -> {target}")
    async with async_session_factory() as db:
        migrated = await SkillService(db).migrate_legacy_packages()
    print(f"materialized {migrated} legacy Skill packages")


if __name__ == "__main__":
    asyncio.run(main())
