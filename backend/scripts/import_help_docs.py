import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from app.core.database import init_db
from app.deps.db import get_db_session
from app.mappers.help_document_mapper import HelpDocumentMapper


DEFAULT_DATA_FILE = Path(__file__).resolve().parents[1] / "app" / "seed" / "help_docs.json"


def load_documents(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Help docs seed file must contain a JSON array")
    for item in data:
        if not item.get("slug") or not item.get("title") or not item.get("content"):
            raise ValueError(f"Invalid help document entry: {item!r}")
    return data


async def import_documents(path: Path, dry_run: bool = False) -> None:
    docs = load_documents(path)
    await init_db()
    async with get_db_session() as db:
        mapper = HelpDocumentMapper(db)
        created = 0
        updated = 0
        for doc in docs:
            existing = await mapper.get_any_by_slug(doc["slug"])
            if existing:
                updated += 1
            else:
                created += 1
            if not dry_run:
                await mapper.upsert_by_slug(doc)
        if dry_run:
            await db.rollback()
        print(
            f"Loaded {len(docs)} help documents from {path}. "
            f"created={created}, updated={updated}, dry_run={dry_run}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Fancy Agent help documents.")
    parser.add_argument("--file", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(import_documents(args.file, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
