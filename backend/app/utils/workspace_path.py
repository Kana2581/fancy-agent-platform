"""Session 工作区路径安全 + 配额检查工具。

所有 builtin workspace 工具的路径都必须先过 safe_resolve()，
写操作必须先过 check_quota()。
"""
import asyncio
import time
from pathlib import Path
from typing import Dict, Set, Tuple

from app.core.config import settings


_USER_USED_CACHE: Dict[int, Tuple[float, int]] = {}
_USER_USED_TTL_SECONDS = 30.0


# 禁止下载/呈现给浏览器的危险扩展名（即便允许写入，也禁止 ws_present 暴露）
DANGEROUS_DOWNLOAD_EXTS: Set[str] = {
    ".exe", ".bat", ".cmd", ".com", ".scr", ".msi",
    ".dll", ".so", ".dylib",
    ".ps1", ".vbs", ".jse", ".jar",
    ".html", ".htm", ".svg",  # 防 inline XSS
}


class PathTraversalError(ValueError):
    """路径越界或非法。"""


class QuotaExceededError(ValueError):
    """workspace 配额超限。"""


def get_workspace_root(user_id: int, session_id: str) -> Path:
    return Path(settings.WORKSPACE_DIR) / str(user_id) / session_id


def ensure_workspace(user_id: int, session_id: str) -> Path:
    root = get_workspace_root(user_id, session_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_resolve(user_id: int, session_id: str, user_path: str) -> Path:
    """把 agent 传入的相对路径解析到 session 工作区下。

    校验顺序：
    1. 拒绝绝对路径（含 Windows 盘符）
    2. 解析符号链接（resolve）
    3. 必须 is_relative_to 工作区根
    """
    if not user_path or user_path.strip() == "":
        raise PathTraversalError("路径不能为空")

    cleaned = user_path.strip().lstrip("/").lstrip("\\")
    candidate = Path(cleaned)
    if candidate.is_absolute() or (len(cleaned) >= 2 and cleaned[1] == ":"):
        raise PathTraversalError(f"不允许绝对路径: {user_path}")

    root = ensure_workspace(user_id, session_id).resolve()
    full = (root / cleaned).resolve()

    try:
        full.relative_to(root)
    except ValueError:
        raise PathTraversalError(f"路径越界: {user_path}")

    return full


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for entry in path.rglob("*"):
        try:
            if entry.is_file():
                total += entry.stat().st_size
        except OSError:
            continue
    return total


def _count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for entry in path.rglob("*") if entry.is_file())


def invalidate_user_used_cache(user_id: int) -> None:
    _USER_USED_CACHE.pop(user_id, None)


async def _get_user_used_cached(user_id: int) -> int:
    """带 TTL 缓存的用户目录用量；FS walk 走 to_thread 不阻塞事件循环。"""
    now = time.monotonic()
    cached = _USER_USED_CACHE.get(user_id)
    if cached and now - cached[0] < _USER_USED_TTL_SECONDS:
        return cached[1]
    user_root = Path(settings.WORKSPACE_DIR) / str(user_id)
    used = await asyncio.to_thread(_dir_size_bytes, user_root)
    _USER_USED_CACHE[user_id] = (now, used)
    return used


async def check_quota(
    user_id: int,
    session_id: str,
    incoming_bytes: int,
    final_file_size: int | None = None,
) -> None:
    """写入前调用：检查单文件、session、用户总配额、单目录文件数。

    - incoming_bytes: 本次新增写入字节数（用于会话/用户总额累加），edit 时为 delta。
    - final_file_size: 写完后该文件的总大小；若不传则按 incoming_bytes 计算。
      用于卡住单文件上限，避免 ws_edit 用小 delta 累积绕过 max_file。
    """
    max_file = settings.WORKSPACE_MAX_FILE_SIZE_MB * 1024 * 1024
    per_file_check = final_file_size if final_file_size is not None else incoming_bytes
    if per_file_check > max_file:
        raise QuotaExceededError(
            f"单文件超限：{per_file_check / 1024 / 1024:.1f}MB > "
            f"{settings.WORKSPACE_MAX_FILE_SIZE_MB}MB"
        )

    session_root = get_workspace_root(user_id, session_id)
    session_used = await asyncio.to_thread(_dir_size_bytes, session_root)
    max_session = settings.WORKSPACE_MAX_SESSION_MB * 1024 * 1024
    if session_used + incoming_bytes > max_session:
        raise QuotaExceededError(
            f"Session 配额超限：已用 {session_used / 1024 / 1024:.1f}MB + 新增 "
            f"{incoming_bytes / 1024 / 1024:.1f}MB > {settings.WORKSPACE_MAX_SESSION_MB}MB"
        )

    user_used = await _get_user_used_cached(user_id)
    max_user = settings.WORKSPACE_MAX_USER_GB * 1024 * 1024 * 1024
    if user_used + incoming_bytes > max_user:
        # 缓存可能滞后，临界时强制刷一次再判
        invalidate_user_used_cache(user_id)
        user_used = await _get_user_used_cached(user_id)
        if user_used + incoming_bytes > max_user:
            raise QuotaExceededError(
                f"用户配额超限：已用 {user_used / 1024 / 1024:.1f}MB > "
                f"{settings.WORKSPACE_MAX_USER_GB * 1024}MB"
            )

    session_file_count = await asyncio.to_thread(_count_files, session_root)
    if session_file_count >= settings.WORKSPACE_MAX_FILES_PER_DIR:
        raise QuotaExceededError(
            f"Session 文件数超限：>= {settings.WORKSPACE_MAX_FILES_PER_DIR}"
        )

    # 写入会改变用户总量，主动让缓存里的累计值递增
    cached = _USER_USED_CACHE.get(user_id)
    if cached:
        _USER_USED_CACHE[user_id] = (cached[0], cached[1] + max(incoming_bytes, 0))


def is_safe_download_ext(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext not in DANGEROUS_DOWNLOAD_EXTS


def relative_to_root(user_id: int, session_id: str, full: Path) -> str:
    """把绝对路径反向转成 agent 视角的相对路径（用 / 分隔）。"""
    root = get_workspace_root(user_id, session_id).resolve()
    try:
        rel = full.resolve().relative_to(root)
    except ValueError:
        return str(full)
    return rel.as_posix()
