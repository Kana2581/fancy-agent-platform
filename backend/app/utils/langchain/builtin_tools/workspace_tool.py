"""Session 工作区文件操作工具集。

每个 session 在 /data/workspaces/{user_id}/{session_id}/ 下有独立的可写工作区。
agent 通过这些工具读写文件、向用户呈现下载。所有路径走 safe_resolve 校验，
写操作前走 check_quota，禁止越界、禁止超配额、禁止暴露危险扩展名下载。
"""
import json
from pathlib import Path
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import settings
from app.deps.db import get_db_session
from app.mappers.chat_file_mapper import ChatFileMapper
from app.mappers.chat_file_content_mapper import ChatFileContentMapper
from app.utils.workspace_path import (
    DANGEROUS_DOWNLOAD_EXTS,
    PathTraversalError,
    QuotaExceededError,
    check_quota,
    ensure_workspace,
    get_workspace_root,
    is_safe_download_ext,
    relative_to_root,
    safe_resolve,
)


class WsListInput(BaseModel):
    path: str = Field(default="", description="相对路径，留空列工作区根目录")


class WsReadInput(BaseModel):
    path: str = Field(description="工作区相对路径，例如 report.md 或 dir/sub.txt")
    offset: int = Field(default=0, description="起始字符偏移")
    limit: int = Field(default=20000, description="最多读取字符数，硬上限 WORKSPACE_READ_MAX_CHARS")


class WsWriteInput(BaseModel):
    path: str = Field(description="工作区相对路径；父目录会自动创建")
    content: str = Field(description="完整文件内容（覆盖写入）")


class WsEditInput(BaseModel):
    path: str = Field(description="工作区相对路径")
    old: str = Field(description="要替换的旧字符串（必须唯一，除非 replace_all=true）")
    new: str = Field(description="替换后的新字符串")
    replace_all: bool = Field(default=False, description="是否替换全部出现")


class WsDeleteInput(BaseModel):
    path: str = Field(description="工作区相对文件路径")


class WsPresentInput(BaseModel):
    paths: List[str] = Field(description="一组工作区相对路径，将作为下载卡呈现给用户")
    title: Optional[str] = Field(default=None, description="可选的卡片标题/说明")


class UploadsReadInput(BaseModel):
    file_id: int = Field(description="ChatFile.id，从 uploads_list 取得")


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, ensure_ascii=False)


def _ok(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def _build_object_key(user_id: int, session_id: str, target: Path) -> str:
    """把工作区内绝对路径反推成 ChatFile.object_key（统一用 / 分隔）。"""
    ws_root = Path(settings.WORKSPACE_DIR)
    try:
        return str(target.relative_to(ws_root)).replace("\\", "/")
    except ValueError:
        return f"{user_id}/{session_id}/{target.name}"


async def _register_workspace_file(
    user_id: int,
    session_id: str,
    target: Path,
) -> Optional[int]:
    """ws_write / ws_edit 后调用：把文件登记/刷新为 ChatFile 行。

    - 危险扩展名（.exe/.html 等）跳过，不登记
    - 已存在则只在 size 变化时刷新
    - 返回 chat_file.id；跳过/异常时返回 None
    """
    if not target.exists() or not target.is_file():
        return None
    if not is_safe_download_ext(target.name):
        return None
    try:
        size = target.stat().st_size
        ext = target.suffix.lower().lstrip(".")
        object_key = _build_object_key(user_id, session_id, target)
        async with get_db_session() as db:
            mapper = ChatFileMapper(db)
            existing = await mapper.get_workspace_file(
                session_id=session_id,
                user_id=user_id,
                object_key=object_key,
            )
            if existing is not None:
                if existing.file_size != size:
                    await mapper.update_by_id(existing.id, {"file_size": size})
                await db.commit()
                return existing.id
            chat_file = await mapper.create_from_dict({
                "file_name": target.name,
                "file_ext": ext,
                "file_size": size,
                "content_type": None,
                "storage_type": "workspace",
                "object_key": object_key,
                "md5": None,
                "upload_user_id": user_id,
                "session_id": session_id,
                "parse_status": 0,
            })
            await db.commit()
            return chat_file.id
    except Exception:
        # 自动登记是辅助路径，不能把主 tool 的成功结果搞挂
        return None


async def _unregister_workspace_file(
    user_id: int,
    session_id: str,
    target: Path,
) -> None:
    """ws_delete 后调用：清理对应的 ChatFile 行，避免面板留下 404 幽灵条目。"""
    try:
        object_key = _build_object_key(user_id, session_id, target)
        async with get_db_session() as db:
            mapper = ChatFileMapper(db)
            existing = await mapper.get_workspace_file(
                session_id=session_id,
                user_id=user_id,
                object_key=object_key,
            )
            if existing is not None:
                await mapper.delete_by_id(existing.id)
                await db.commit()
    except Exception:
        return


def build_workspace_tools(user_id: int, session_id: str) -> List[BaseTool]:

    class WsListTool(BaseTool):
        name: str = "ws_list"
        description: str = (
            "列出工作区目录下的文件和子目录。返回 [{name, type, size}]。"
            "工作区是当前会话独立的存储空间，与用户上传的 uploads 分开。"
        )
        args_schema: Type[BaseModel] = WsListInput

        async def _arun(self, path: str = "") -> str:
            try:
                target = ensure_workspace(user_id, session_id)
                if path:
                    target = safe_resolve(user_id, session_id, path)
                if not target.exists():
                    return _ok({"path": path or "/", "entries": []})
                if not target.is_dir():
                    return _err(f"不是目录: {path}")
                entries = []
                for entry in sorted(target.iterdir()):
                    try:
                        if entry.is_dir():
                            entries.append({"name": entry.name, "type": "dir"})
                        else:
                            entries.append({
                                "name": entry.name,
                                "type": "file",
                                "size": entry.stat().st_size,
                            })
                    except OSError:
                        continue
                return _ok({"path": path or "/", "entries": entries})
            except PathTraversalError as e:
                return _err(str(e))
            except Exception as e:
                return _err(f"列目录失败: {e}")

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class WsReadTool(BaseTool):
        name: str = "ws_read"
        description: str = (
            "读取工作区文本文件内容。二进制文件会拒绝。支持 offset/limit 分段读取。"
        )
        args_schema: Type[BaseModel] = WsReadInput

        async def _arun(self, path: str, offset: int = 0, limit: int = 20000) -> str:
            try:
                target = safe_resolve(user_id, session_id, path)
                if not target.exists() or not target.is_file():
                    return _err(f"文件不存在: {path}")
                max_chars = settings.WORKSPACE_READ_MAX_CHARS
                limit = min(max(limit, 1), max_chars)
                try:
                    text = target.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    return _err(f"二进制文件无法 ws_read，请用 ws_present 呈现给用户下载: {path}")
                end = min(offset + limit, len(text))
                return _ok({
                    "path": path,
                    "content": text[offset:end],
                    "total_chars": len(text),
                    "offset": offset,
                    "returned_chars": end - offset,
                })
            except PathTraversalError as e:
                return _err(str(e))
            except Exception as e:
                return _err(f"读文件失败: {e}")

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class WsWriteTool(BaseTool):
        name: str = "ws_write"
        description: str = (
            "把完整内容写入工作区文件（覆盖写）。父目录自动创建。"
            "受单文件/会话/用户配额限制。"
            "写入成功后会自动在用户的「工作区文件」面板出现可下载条目，无需再调用 ws_present。"
        )
        args_schema: Type[BaseModel] = WsWriteInput

        async def _arun(self, path: str, content: str) -> str:
            try:
                target = safe_resolve(user_id, session_id, path)
                new_size = len(content.encode("utf-8"))
                old_size = target.stat().st_size if target.exists() and target.is_file() else 0
                delta = max(new_size - old_size, 0)
                await check_quota(user_id, session_id, delta, final_file_size=new_size)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                file_id = await _register_workspace_file(user_id, session_id, target)
                return _ok({
                    "path": relative_to_root(user_id, session_id, target),
                    "size": new_size,
                    "file_id": file_id,
                })
            except (PathTraversalError, QuotaExceededError) as e:
                return _err(str(e))
            except Exception as e:
                return _err(f"写文件失败: {e}")

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class WsEditTool(BaseTool):
        name: str = "ws_edit"
        description: str = (
            "对工作区已有文本文件做字符串替换。"
            "默认要求 old 在文件中唯一；replace_all=true 时全部替换。"
        )
        args_schema: Type[BaseModel] = WsEditInput

        async def _arun(self, path: str, old: str, new: str, replace_all: bool = False) -> str:
            try:
                target = safe_resolve(user_id, session_id, path)
                if not target.exists() or not target.is_file():
                    return _err(f"文件不存在: {path}")
                try:
                    text = target.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    return _err("二进制文件不支持 ws_edit")
                count = text.count(old)
                if count == 0:
                    return _err(f"未找到 old 字符串")
                if count > 1 and not replace_all:
                    return _err(f"old 字符串出现 {count} 次，请加 replace_all=true 或提供更具体的上下文")
                new_text = text.replace(old, new) if replace_all else text.replace(old, new, 1)
                new_size = len(new_text.encode("utf-8"))
                old_size = len(text.encode("utf-8"))
                await check_quota(
                    user_id,
                    session_id,
                    max(new_size - old_size, 0),
                    final_file_size=new_size,
                )
                target.write_text(new_text, encoding="utf-8")
                file_id = await _register_workspace_file(user_id, session_id, target)
                return _ok({
                    "path": relative_to_root(user_id, session_id, target),
                    "replaced": count if replace_all else 1,
                    "file_id": file_id,
                })
            except (PathTraversalError, QuotaExceededError) as e:
                return _err(str(e))
            except Exception as e:
                return _err(f"编辑失败: {e}")

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class WsDeleteTool(BaseTool):
        name: str = "ws_delete"
        description: str = "删除工作区文件。注意不会进回收站。"
        args_schema: Type[BaseModel] = WsDeleteInput

        async def _arun(self, path: str) -> str:
            try:
                target = safe_resolve(user_id, session_id, path)
                if not target.exists():
                    return _err(f"文件不存在: {path}")
                if target.is_dir():
                    return _err(f"不允许通过 ws_delete 删目录")
                target.unlink()
                await _unregister_workspace_file(user_id, session_id, target)
                return _ok({"deleted": path})
            except PathTraversalError as e:
                return _err(str(e))
            except Exception as e:
                return _err(f"删除失败: {e}")

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class WsPresentTool(BaseTool):
        name: str = "ws_present"
        description: str = (
            "（辅助工具）把工作区里的若干文件强制刷新登记到「工作区文件」面板，"
            "并返回每个文件的 file_id。"
            "正常情况下 ws_write/ws_edit 写入后已经自动登记，不需要再调用本工具；"
            "仅在你需要拿到 file_id 或整理一组文件的展示时使用。"
            "禁止呈现可执行/可渲染文件（.exe/.bat/.dll/.html 等）。"
        )
        args_schema: Type[BaseModel] = WsPresentInput

        async def _arun(self, paths: List[str], title: Optional[str] = None) -> str:
            try:
                presented = []
                for p in paths:
                    try:
                        target = safe_resolve(user_id, session_id, p)
                    except PathTraversalError as e:
                        presented.append({"path": p, "error": str(e)})
                        continue
                    if not target.exists() or not target.is_file():
                        presented.append({"path": p, "error": "文件不存在"})
                        continue
                    if not is_safe_download_ext(target.name):
                        ext = target.suffix.lower()
                        presented.append({
                            "path": p,
                            "error": f"扩展名 {ext} 禁止下载暴露（防 XSS/恶意可执行）",
                        })
                        continue
                    file_id = await _register_workspace_file(user_id, session_id, target)
                    presented.append({
                        "file_id": file_id,
                        "name": target.name,
                        "size": target.stat().st_size,
                        "path": p,
                    })
                return _ok({
                    "presented_files": presented,
                    "title": title or "",
                })
            except Exception as e:
                return _err(f"present 失败: {e}")

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class UploadsListTool(BaseTool):
        name: str = "uploads_list"
        description: str = (
            "列出当前 session 中用户上传的文件（只读）。"
            "返回 [{file_id, name, ext, size}]。"
            "如需修改这些文件的内容，请用 uploads_read 读取后 ws_write 复制到工作区。"
        )
        args_schema: Type[BaseModel] = BaseModel

        async def _arun(self, **kwargs) -> str:
            async with get_db_session() as db:
                files = await ChatFileMapper(db).list_by_session(session_id)
                return _ok({
                    "files": [
                        {
                            "file_id": f.id,
                            "name": f.file_name,
                            "ext": f.file_ext,
                            "size": f.file_size,
                            "storage_type": f.storage_type,
                        }
                        for f in files
                        if f.storage_type != "workspace"  # 不暴露 ws_present 产出的文件
                    ]
                })

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class UploadsReadTool(BaseTool):
        name: str = "uploads_read"
        description: str = (
            "读取用户上传文件的解析文本内容（仅文本/PDF/DOCX，图片不可读）。"
            "uploads 是只读的：不能写、不能删；要修改请复制到工作区。"
        )
        args_schema: Type[BaseModel] = UploadsReadInput

        async def _arun(self, file_id: int) -> str:
            async with get_db_session() as db:
                file_mapper = ChatFileMapper(db)
                content_mapper = ChatFileContentMapper(db)
                f = await file_mapper.get_by_id(file_id)
                if not f or f.session_id != session_id:
                    return _err(f"未找到 file_id={file_id} 或不属于当前会话")
                if f.storage_type == "workspace":
                    return _err("workspace 文件请用 ws_read，不是 uploads_read")
                content = await content_mapper.get_by_file_id(file_id)
                if not content:
                    return _err(f"文件 {f.file_name} 尚未解析或不可解析（如图片）")
                return _ok({
                    "file_id": file_id,
                    "name": f.file_name,
                    "content": content.content,
                })

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    return [
        WsListTool(),
        WsReadTool(),
        WsWriteTool(),
        WsEditTool(),
        WsDeleteTool(),
        WsPresentTool(),
        UploadsListTool(),
        UploadsReadTool(),
    ]
