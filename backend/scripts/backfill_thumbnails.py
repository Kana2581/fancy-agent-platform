"""一次性回填脚本：为已有的 generated 图片生成 .thumb.webp 缩略图。

用法：
    cd backend
    uv run python scripts/backfill_thumbnails.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.utils.image.base_adapter import (  # noqa: E402
    THUMBNAIL_SUFFIX,
    generate_thumbnail,
)

SOURCE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def main() -> None:
    upload_dir = Path(getattr(settings, "UPLOAD_DIR", "/data/uploads"))
    root = upload_dir / "generated"
    if not root.exists():
        print(f"No generated dir at {root}, nothing to do.")
        return

    done = skipped = failed = 0
    for src in root.rglob("*"):
        if not src.is_file():
            continue
        if src.name.endswith(THUMBNAIL_SUFFIX):
            continue
        if src.suffix.lower() not in SOURCE_EXTS:
            continue

        dst = src.with_name(src.name + THUMBNAIL_SUFFIX)
        if dst.exists():
            skipped += 1
            continue

        try:
            generate_thumbnail(src, dst)
            done += 1
            if done % 20 == 0:
                print(f"  ... {done} done, {skipped} skipped, {failed} failed")
        except Exception as exc:
            failed += 1
            print(f"  FAIL {src}: {exc}")

    print(f"\nFinished: {done} generated, {skipped} skipped, {failed} failed.")


if __name__ == "__main__":
    main()
