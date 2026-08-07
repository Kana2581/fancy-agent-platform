"""Register files produced by sandbox execution with the workspace UI."""

import asyncio
from pathlib import Path
from typing import List, Optional

from app.core.logging_config import get_logger
from app.utils.workspace_path import relative_to_root

logger = get_logger(__name__)

_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp"}


async def _publish_image_to_generated(src: Path) -> Optional[str]:
    try:
        from app.utils.image.base_adapter import build_image_url, save_generated_image

        data = await asyncio.to_thread(src.read_bytes)
        ext = src.suffix.lstrip(".") or "png"
        object_key = await save_generated_image(data, ext)
        return build_image_url(object_key)
    except Exception:
        logger.exception("sandbox publish image to generated failed")
        return None


async def handle_sandbox_products(
    user_id: int,
    session_id: str,
    workdir: Path,
    produced: List[object],
) -> List[dict]:
    """Register changed workspace files and publish previewable images."""
    from app.utils.langchain.builtin_tools.workspace_tool import _register_workspace_file

    files: List[dict] = []
    for item in produced:
        if isinstance(item, dict):
            rel = str(item.get("path", ""))
            size = item.get("size")
        else:
            rel = str(item)
            size = None
        target = workdir / rel
        if not target.exists() or not target.is_file():
            continue
        entry: dict = {"path": relative_to_root(user_id, session_id, target)}
        try:
            entry["size"] = int(size) if size is not None else target.stat().st_size
        except OSError:
            pass
        file_id = await _register_workspace_file(
            user_id,
            session_id,
            entry["path"],
            entry.get("size"),
        )
        if file_id is not None:
            entry["file_id"] = file_id
        if target.suffix.lower().lstrip(".") in _IMAGE_EXTS:
            url = await _publish_image_to_generated(target)
            if url:
                entry["url"] = url
        files.append(entry)
    return files
