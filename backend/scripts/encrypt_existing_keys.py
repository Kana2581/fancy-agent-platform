"""一次性迁移脚本：把 llms / image_tools 表里存量的明文 api_key 重新加密入库。

幂等：已是密文的行会被自动跳过，可重复执行。

用法：
    cd backend
    uv run python scripts/encrypt_existing_keys.py

注意：必须在 backend/ 目录下运行（config 走相对 .env 路径），
且使用的加密密钥须与运行服务时一致（APP_ENCRYPTION_KEY 或回退的 SECRET_KEY）。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app.core.crypto import _get_fernet, encrypt_str  # noqa: E402
from app.core.database import engine  # noqa: E402

# 表名 -> 是否允许 api_key 为空（仅用于日志）
TABLES = ["llms", "image_tools"]


def _is_already_encrypted(value: str) -> bool:
    try:
        _get_fernet().decrypt(value.encode("utf-8"))
        return True
    except Exception:
        return False


async def _migrate_table(conn, table: str) -> tuple[int, int]:
    rows = (await conn.execute(
        text(f"SELECT id, api_key FROM {table}")
    )).fetchall()

    encrypted = skipped = 0
    for row_id, api_key in rows:
        if api_key is None or api_key == "":
            skipped += 1
            continue
        if _is_already_encrypted(api_key):
            skipped += 1
            continue
        await conn.execute(
            text(f"UPDATE {table} SET api_key = :v WHERE id = :id"),
            {"v": encrypt_str(api_key), "id": row_id},
        )
        encrypted += 1
    return encrypted, skipped


async def main() -> None:
    async with engine.begin() as conn:
        for table in TABLES:
            encrypted, skipped = await _migrate_table(conn, table)
            print(f"{table}: {encrypted} encrypted, {skipped} skipped (already encrypted / empty)")
    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
