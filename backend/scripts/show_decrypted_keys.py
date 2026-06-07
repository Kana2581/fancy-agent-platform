"""只读脚本：打印 llms / image_tools 里 api_key 的解密明文，方便人工核对。

注意：纯 SQL 无法解密 Fernet 密文，必须经本脚本（Python + 密钥）解密。

用法：
    cd backend
    uv run python scripts/show_decrypted_keys.py

使用的密钥须与运行服务时一致（APP_ENCRYPTION_KEY 或回退的 SECRET_KEY）。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app.core.crypto import decrypt_str  # noqa: E402
from app.core.database import engine  # noqa: E402

# 表 -> 用于展示的附加列
TABLES = {
    "llms": ["provider", "model_name"],
    "image_tools": ["provider", "name"],
}


async def _dump_table(conn, table: str, extra_cols: list[str]) -> None:
    cols = ", ".join(["id", "api_key", *extra_cols])
    rows = (await conn.execute(text(f"SELECT {cols} FROM {table}"))).mappings().all()
    print(f"\n=== {table} ({len(rows)} rows) ===")
    for row in rows:
        stored = row["api_key"]
        plain = decrypt_str(stored) if stored else ""
        is_cipher = stored not in (None, "") and plain != stored
        tag = "encrypted" if is_cipher else "PLAINTEXT"
        extra = "  ".join(f"{c}={row[c]}" for c in extra_cols)
        print(f"  id={row['id']:<4} [{tag:<9}] key={plain or '(空)'}   {extra}")


async def main() -> None:
    async with engine.connect() as conn:
        for table, extra_cols in TABLES.items():
            await _dump_table(conn, table, extra_cols)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
