"""用户面 workspace API：列文件、下载、删除。

下载强制 Content-Disposition: attachment，禁止浏览器 inline 渲染（防 XSS）。
"""
import asyncio
import os
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from starlette.background import BackgroundTask

from app.core.config import settings
from app.deps.db import get_db_session
from app.deps.user import get_current_user
from app.mappers.chat_file_mapper import ChatFileMapper
from app.models.chat_file import ChatFile
from app.utils.workspace_path import (
    PathTraversalError,
    get_workspace_root,
    is_safe_download_ext,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


class WorkspaceFileOut(BaseModel):
    file_id: int
    name: str
    ext: str
    size: int
    object_key: str
    session_id: str


@router.get("/{session_id}/files", response_model=List[WorkspaceFileOut])
async def list_workspace_files(
    session_id: str,
    user_id: int = Depends(get_current_user),
):
    async with get_db_session() as db:
        result = await db.execute(
            select(ChatFile).where(
                ChatFile.session_id == session_id,
                ChatFile.upload_user_id == user_id,
                ChatFile.storage_type == "workspace",
            )
        )
        files = list(result.scalars().all())
        return [
            WorkspaceFileOut(
                file_id=f.id,
                name=f.file_name,
                ext=f.file_ext,
                size=f.file_size,
                object_key=f.object_key,
                session_id=f.session_id or "",
            )
            for f in files
        ]


@router.get("/files/{file_id}/download")
async def download_workspace_file(
    file_id: int,
    user_id: int = Depends(get_current_user),
):
    async with get_db_session() as db:
        f = await ChatFileMapper(db).get_by_id(file_id)
        if not f or f.upload_user_id != user_id:
            raise HTTPException(status_code=404, detail="文件不存在或无权访问")
        if f.storage_type != "workspace":
            raise HTTPException(status_code=400, detail="该接口仅用于 workspace 文件")
        if not is_safe_download_ext(f.file_name):
            raise HTTPException(status_code=403, detail="该扩展名禁止下载")

        ws_dir = Path(settings.WORKSPACE_DIR)
        full = (ws_dir / f.object_key).resolve()
        try:
            full.relative_to(ws_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="非法路径")
        if not full.exists() or not full.is_file():
            raise HTTPException(status_code=404, detail="物理文件已丢失")

        safe_name = quote(f.file_name)
        return FileResponse(
            path=str(full),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{safe_name}',
                "X-Content-Type-Options": "nosniff",
            },
        )


@router.get("/{session_id}/download-all")
async def download_all_workspace_files(
    session_id: str,
    user_id: int = Depends(get_current_user),
):
    """打包下载当前 session 全部 workspace 文件。

    - 危险扩展名（.exe/.html 等）整体跳过，不进 zip
    - 物理文件丢失的整体跳过
    - 同名冲突走 zipfile 自带的去重（自动加后缀）
    """
    async with get_db_session() as db:
        result = await db.execute(
            select(ChatFile).where(
                ChatFile.session_id == session_id,
                ChatFile.upload_user_id == user_id,
                ChatFile.storage_type == "workspace",
            )
        )
        files = list(result.scalars().all())

    ws_dir = Path(settings.WORKSPACE_DIR).resolve()
    pickable: list[tuple[Path, str]] = []
    seen_arcnames: set[str] = set()
    for f in files:
        if not is_safe_download_ext(f.file_name):
            continue
        try:
            full = (ws_dir / f.object_key).resolve()
            full.relative_to(ws_dir)
        except (ValueError, OSError):
            continue
        if not full.exists() or not full.is_file():
            continue

        # 用 object_key 去掉 user/session 前缀作为 zip 内相对路径，
        # 这样 agent 建出来的目录结构能完整保留
        try:
            rel_to_session = full.relative_to(
                (ws_dir / str(user_id) / session_id).resolve()
            )
            arcname = rel_to_session.as_posix()
        except ValueError:
            arcname = f.file_name

        # 同名兜底（理论上 ws_present 的 (session, object_key) 已去重）
        base_arc = arcname
        counter = 1
        while arcname in seen_arcnames:
            stem = Path(base_arc).stem
            suffix = Path(base_arc).suffix
            parent = Path(base_arc).parent.as_posix()
            new_name = f"{stem}({counter}){suffix}"
            arcname = f"{parent}/{new_name}" if parent and parent != "." else new_name
            counter += 1
        seen_arcnames.add(arcname)
        pickable.append((full, arcname))

    if not pickable:
        raise HTTPException(status_code=404, detail="没有可下载的文件")

    total_bytes = sum(full.stat().st_size for full, _ in pickable)
    max_bytes = settings.WORKSPACE_ZIP_MAX_MB * 1024 * 1024
    if total_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"打包文件总量 {total_bytes / 1024 / 1024:.1f}MB 超过上限 "
                f"{settings.WORKSPACE_ZIP_MAX_MB}MB，请单独下载部分文件"
            ),
        )

    fd, tmp_path = tempfile.mkstemp(suffix=".zip", prefix="ws-")
    os.close(fd)

    def _build_zip(target: str, entries: List[Tuple[Path, str]]) -> None:
        # DEFLATE 是 CPU 密集 + 同步阻塞，必须丢到线程池里跑，否则会卡住事件循环。
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for full, arcname in entries:
                zf.write(full, arcname=arcname)

    try:
        await asyncio.to_thread(_build_zip, tmp_path, pickable)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    zip_filename = f"workspace-{session_id[:8]}.zip"
    safe_name = quote(zip_filename)
    return FileResponse(
        path=tmp_path,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{safe_name}',
            "X-Content-Type-Options": "nosniff",
        },
        background=BackgroundTask(lambda: os.path.exists(tmp_path) and os.unlink(tmp_path)),
    )


@router.delete("/{session_id}/files/{file_id}")
async def delete_workspace_file(
    session_id: str,
    file_id: int,
    user_id: int = Depends(get_current_user),
):
    async with get_db_session() as db:
        mapper = ChatFileMapper(db)
        f = await mapper.get_by_id(file_id)
        if not f or f.upload_user_id != user_id or f.session_id != session_id:
            raise HTTPException(status_code=404, detail="文件不存在")
        if f.storage_type != "workspace":
            raise HTTPException(status_code=400, detail="该接口仅删除 workspace 文件")

        ws_dir = Path(settings.WORKSPACE_DIR)
        full = (ws_dir / f.object_key).resolve()
        try:
            full.relative_to(ws_dir.resolve())
            if full.exists() and full.is_file():
                full.unlink()
        except (ValueError, OSError):
            pass

        await mapper.delete_by_id(file_id)
        await db.commit()
        return {"success": True}
