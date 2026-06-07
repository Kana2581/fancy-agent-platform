"""Generate the MySQL bootstrap schema.

Run from ``backend/``:

    uv run python scripts/generate_mysql_schema.py

By default this dumps the current MySQL database with ``SHOW CREATE TABLE`` so
hand-written indexes, foreign keys, and server defaults stay intact. Use
``--source models`` when you explicitly want DDL compiled from SQLAlchemy
metadata instead.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateIndex, CreateTable

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Importing app.models loads every model module via app/models/__init__.py.
from app import models  # noqa: F401,E402
from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402


HEADER = """SET NAMES utf8mb4;
SET character_set_client = utf8mb4;
ALTER DATABASE fancy_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

"""

AUTO_INCREMENT_OPTION_RE = re.compile(r"\sAUTO_INCREMENT=\d+")


def _compile(statement) -> str:
    dialect = mysql.dialect()
    return str(statement.compile(dialect=dialect)).rstrip()


def _quote_identifier(name: str) -> str:
    return f"`{name.replace('`', '``')}`"


def generate_schema_from_models() -> str:
    parts: list[str] = [HEADER]

    for table in Base.metadata.sorted_tables:
        create_table = _compile(CreateTable(table))
        parts.append(f"{create_table} ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n")

        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            parts.append(f"{_compile(CreateIndex(index))};\n")

        parts.append("\n")

    return "\n".join(parts).rstrip() + "\n"


def _topological_table_order(tables: list[str], dependencies: dict[str, set[str]]) -> list[str]:
    remaining = set(tables)
    ordered: list[str] = []

    while remaining:
        ready = sorted(
            table
            for table in remaining
            if not (dependencies.get(table, set()) & remaining)
        )
        if not ready:
            # Cyclic FKs are not expected here; fall back to deterministic order
            # instead of hiding tables from the output.
            ordered.extend(sorted(remaining))
            break
        ordered.extend(ready)
        remaining.difference_update(ready)

    return ordered


async def generate_schema_from_database() -> str:
    if not settings.DATABASE_URL.startswith("mysql"):
        raise RuntimeError(
            "DATABASE_URL must point at MySQL when using --source database. "
            "Use --source models for offline generation."
        )

    engine = create_async_engine(settings.DATABASE_URL, future=True)
    try:
        async with engine.connect() as conn:
            table_rows = await conn.execute(
                text(
                    """
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                    """
                )
            )
            tables = [row.TABLE_NAME for row in table_rows]

            dependency_rows = await conn.execute(
                text(
                    """
                    SELECT TABLE_NAME, REFERENCED_TABLE_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND REFERENCED_TABLE_NAME IS NOT NULL
                    """
                )
            )
            dependencies: dict[str, set[str]] = {}
            for row in dependency_rows:
                if row.TABLE_NAME != row.REFERENCED_TABLE_NAME:
                    dependencies.setdefault(row.TABLE_NAME, set()).add(
                        row.REFERENCED_TABLE_NAME
                    )

            parts: list[str] = [HEADER]
            for table_name in _topological_table_order(tables, dependencies):
                result = await conn.execute(
                    text(f"SHOW CREATE TABLE {_quote_identifier(table_name)}")
                )
                row = result.mappings().one()
                create_table = AUTO_INCREMENT_OPTION_RE.sub(
                    "",
                    row["Create Table"].rstrip(),
                )
                parts.append(f"{create_table};\n\n")

            return "\n".join(parts).rstrip() + "\n"
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=("database", "models"),
        default="database",
        help="Where to read schema from. Default: database.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_DIR / "db_init" / "01table_create.sql",
        help="Output SQL file path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    schema = (
        asyncio.run(generate_schema_from_database())
        if args.source == "database"
        else generate_schema_from_models()
    )
    args.output.write_text(schema, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
