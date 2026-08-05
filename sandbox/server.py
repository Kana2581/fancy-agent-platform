"""Unified per-session workspace runtime.

All agent workspace mutations and code execution enter through this service.  The
backend owns authorization, quotas, and ChatFile records; this process owns the
filesystem boundary and serializes operations for one session.
"""
import asyncio
import os
import signal
import shlex
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import sandbox_runner

app = FastAPI(title="code-sandbox", docs_url=None, redoc_url=None)

WORKSPACES_ROOT = Path(os.environ.get("WORKSPACES_ROOT", "/workspaces")).resolve()
EXEC_TIMEOUT = int(os.environ.get("SANDBOX_EXEC_TIMEOUT", "30"))
MAX_OUTPUT_BYTES = int(os.environ.get("SANDBOX_MAX_OUTPUT_BYTES", str(256 * 1024)))
_exec_semaphore = asyncio.Semaphore(int(os.environ.get("SANDBOX_CONCURRENCY", "1")))
_workspace_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class ExecRequest(BaseModel):
    # Existing fields remain compatible with the original Python-only endpoint.
    code: Optional[str] = None
    rel_dir: str
    timeout: int = Field(default=EXEC_TIMEOUT)
    script_path: Optional[str] = None
    runtime: Literal["python", "bash"] = "python"
    command: Optional[str] = None
    cwd: Optional[str] = None
    max_file_bytes: int = Field(gt=0)
    max_session_bytes: int = Field(gt=0)
    max_user_bytes: int = Field(gt=0)
    max_files: int = Field(gt=0)


class WorkspaceRequest(BaseModel):
    rel_dir: str


class ListRequest(WorkspaceRequest):
    path: str = ""


class ReadRequest(WorkspaceRequest):
    path: str
    offset: int = 0
    limit: int = 20000


class WriteRequest(WorkspaceRequest):
    path: str
    content: str


class EditRequest(WorkspaceRequest):
    path: str
    old: str
    new: str
    replace_all: bool = False
    dry_run: bool = False


class DeleteRequest(WorkspaceRequest):
    path: str


class StatRequest(WorkspaceRequest):
    path: str


def _error(message: str, **extra: object) -> dict:
    return {"error": message, **extra}


def _resolve_rel_dir(rel_dir: str, create: bool = True) -> Path:
    raw = (rel_dir or "").strip()
    candidate = Path(raw)
    if not raw or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("rel_dir 非法")
    root = WORKSPACES_ROOT.resolve()
    workdir = (root / candidate).resolve()
    if workdir == root or root not in workdir.parents:
        raise ValueError("rel_dir 越界")
    if create:
        workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def _resolve_path(workdir: Path, user_path: str, *, allow_root: bool = False) -> Path:
    raw = (user_path or "").strip()
    if not raw and allow_root:
        return workdir
    candidate = Path(raw)
    if not raw or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("路径非法")
    target = (workdir / candidate).resolve()
    if target != workdir and workdir not in target.parents:
        raise ValueError("路径越界")
    # A symlink is never a valid workspace object, even if it points back inside.
    cursor = workdir
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise ValueError("不允许符号链接")
    return target


def _snapshot(workdir: Path) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for entry in workdir.rglob("*"):
        try:
            if entry.is_file() and not entry.is_symlink():
                stat = entry.stat()
                result[entry.relative_to(workdir).as_posix()] = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            continue
    return result


def _changes(workdir: Path, before: dict[str, tuple[int, int]]) -> tuple[list[str], list[dict], list[str]]:
    after = _snapshot(workdir)
    changed = sorted(path for path, metadata in after.items() if before.get(path) != metadata)
    deleted = sorted(path for path in before if path not in after)
    return changed, [{"path": path, "size": after[path][0]} for path in changed], deleted


def _dir_size_bytes(path: Path) -> int:
    return sum(metadata[0] for metadata in _snapshot(path).values())


def _validate_exec_quota(stage: Path, workdir: Path, req: ExecRequest) -> Optional[str]:
    staged = _snapshot(stage)
    oversized = next((size for size, _ in staged.values() if size > req.max_file_bytes), None)
    if oversized is not None:
        return f"单文件超限：{oversized / 1024 / 1024:.1f}MB"

    staged_size = sum(size for size, _ in staged.values())
    if staged_size > req.max_session_bytes:
        return f"Session 配额超限：{staged_size / 1024 / 1024:.1f}MB"
    if len(staged) > req.max_files:
        return f"Session 文件数超限：{len(staged)} > {req.max_files}"

    # The staging directory is outside the user's workspace tree. Replace the old
    # session size with the staged size to calculate the post-commit user usage.
    user_root = workdir.parent
    user_size = _dir_size_bytes(user_root) - _dir_size_bytes(workdir) + staged_size
    if user_size > req.max_user_bytes:
        return f"用户配额超限：{user_size / 1024 / 1024:.1f}MB"
    return None


def _stage_workspace(workdir: Path) -> Path:
    staging_root = WORKSPACES_ROOT / ".exec-staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="workspace-", dir=staging_root))
    shutil.copytree(workdir, stage, dirs_exist_ok=True, symlinks=True)
    return stage


def _commit_staged_workspace(stage: Path, workdir: Path) -> None:
    backup = stage.parent / f"{stage.name}.previous"
    try:
        os.replace(workdir, backup)
        os.replace(stage, workdir)
    except OSError:
        if backup.exists() and not workdir.exists():
            os.replace(backup, workdir)
        raise
    else:
        shutil.rmtree(backup, ignore_errors=True)


def _truncate(value: str) -> str:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_OUTPUT_BYTES:
        return value
    return encoded[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore") + "\n[输出已截断]"


def _bwrap_command(workdir: Path, meta_dir: Optional[Path] = None) -> list[str]:
    command = [
        "bwrap", "--die-with-parent", "--new-session", "--unshare-user", "--uid", "0", "--gid", "0",
        "--unshare-pid", "--unshare-net", "--clearenv",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/usr/local", "/usr/local",
        "--ro-bind", "/bin", "/bin", "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64", "--ro-bind", "/etc", "/etc",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--bind", str(workdir), "/workspace", "--chdir", "/workspace",
        "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
        "--setenv", "HOME", "/tmp", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
    ]
    if meta_dir:
        command += ["--ro-bind", str(meta_dir), "/meta"]
    return command


def _bwrap_healthy() -> bool:
    try:
        # This validates the exact namespace primitives used for every execution.
        result = subprocess.run(
            _bwrap_command(WORKSPACES_ROOT) + ["--", "/bin/sh", "-c", "test ! -e /workspaces && touch /tmp/probe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _run_bash(command: str, workdir: Path, cwd: Optional[str], timeout: int) -> dict:
    if not command:
        return _error("bash 需要 command", stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])
    try:
        if cwd:
            _resolve_path(workdir, cwd)
            workspace_cwd = "/workspace/" + cwd.replace("\\", "/")
            shell_prefix = f"cd -- {shlex.quote(workspace_cwd)} && "
        else:
            shell_prefix = ""
        before = _snapshot(workdir)
        process = subprocess.Popen(
            _bwrap_command(workdir) + ["--", "/bin/bash", "-lc", shell_prefix + command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            return _error(f"执行超时（超过 {timeout} 秒）", stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])
        produced, changed_files, deleted_files = _changes(workdir, before)
        return {"stdout": _truncate(stdout), "stderr": _truncate(stderr), "exit_code": process.returncode,
                "produced": produced, "changed_files": changed_files, "deleted_files": deleted_files}
    except ValueError as exc:
        return _error(str(exc), stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])
    except Exception as exc:
        return _error(f"bash 执行失败: {exc}", stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])


def _run_python(req: ExecRequest, workdir: Path, timeout: int) -> dict:
    try:
        script = _resolve_path(workdir, req.script_path) if req.script_path else None
    except ValueError as exc:
        return _error(str(exc), stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])

    def builder(meta_dir: Path, runner: Path, user_code: Path, _workdir: Path) -> list[str]:
        inside_code = "/workspace/" + req.script_path.replace("\\", "/") if req.script_path else "/meta/user_code.py"
        return _bwrap_command(workdir, meta_dir) + [
            "--setenv", "SANDBOX_USER_CODE", inside_code,
            "--setenv", "SANDBOX_OUTPUT_DIR", "/workspace",
            "--", "/usr/local/bin/python", "/meta/_runner.py",
        ]

    before = _snapshot(workdir)
    result = sandbox_runner.execute(
        code=req.code, workdir=str(workdir), timeout=timeout,
        script_path=str(script) if script else None, command_builder=builder,
    )
    produced, changed_files, deleted_files = _changes(workdir, before)
    result["produced"] = produced
    result["changed_files"] = changed_files
    result["deleted_files"] = deleted_files
    result["stdout"] = _truncate(result.get("stdout", ""))
    result["stderr"] = _truncate(result.get("stderr", ""))
    return result


@app.get("/health")
async def health() -> dict:
    if not _bwrap_healthy():
        raise HTTPException(status_code=503, detail="bubblewrap namespace isolation unavailable")
    return {"status": "ok"}


@app.post("/exec")
async def exec_code(req: ExecRequest) -> dict:
    try:
        workdir = _resolve_rel_dir(req.rel_dir)
    except ValueError as exc:
        return _error(str(exc), stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])
    if not _bwrap_healthy():
        return _error("bubblewrap 隔离不可用，拒绝执行", stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])
    timeout = max(1, min(req.timeout, 120))
    async with _workspace_locks[req.rel_dir]:
        async with _exec_semaphore:
            loop = asyncio.get_running_loop()
            stage = await loop.run_in_executor(None, _stage_workspace, workdir)
            try:
                if req.runtime == "bash":
                    result = await loop.run_in_executor(None, _run_bash, req.command or "", stage, req.cwd, timeout)
                else:
                    result = await loop.run_in_executor(None, _run_python, req, stage, timeout)
                if result.get("error"):
                    return result
                quota_error = await loop.run_in_executor(None, _validate_exec_quota, stage, workdir, req)
                if quota_error:
                    return _error(quota_error, stdout=result.get("stdout", ""), stderr=result.get("stderr", ""),
                                  exit_code=result.get("exit_code", -1), produced=[], changed_files=[], deleted_files=[])
                await loop.run_in_executor(None, _commit_staged_workspace, stage, workdir)
                return result
            finally:
                if stage.exists():
                    await loop.run_in_executor(None, shutil.rmtree, stage, True)


@app.post("/workspace/list")
async def workspace_list(req: ListRequest) -> dict:
    try:
        workdir = _resolve_rel_dir(req.rel_dir)
        async with _workspace_locks[req.rel_dir]:
            target = _resolve_path(workdir, req.path, allow_root=True)
            if not target.exists():
                return {"path": req.path or "/", "entries": []}
            if not target.is_dir():
                return _error(f"不是目录: {req.path}")
            entries = []
            for entry in sorted(target.iterdir()):
                if entry.is_symlink():
                    continue
                entries.append({"name": entry.name, "type": "dir" if entry.is_dir() else "file",
                                **({} if entry.is_dir() else {"size": entry.stat().st_size})})
            return {"path": req.path or "/", "entries": entries}
    except (ValueError, OSError) as exc:
        return _error(str(exc))


@app.post("/workspace/read")
async def workspace_read(req: ReadRequest) -> dict:
    try:
        workdir = _resolve_rel_dir(req.rel_dir)
        async with _workspace_locks[req.rel_dir]:
            target = _resolve_path(workdir, req.path)
            if not target.is_file():
                return _error(f"文件不存在: {req.path}")
            try:
                content = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return _error(f"二进制文件无法 ws_read，请用 ws_present 呈现给用户下载: {req.path}")
            offset = max(0, req.offset)
            limit = min(max(req.limit, 1), 20000)
            end = min(offset + limit, len(content))
            return {"path": req.path, "content": content[offset:end], "total_chars": len(content),
                    "offset": offset, "returned_chars": end - offset}
    except (ValueError, OSError) as exc:
        return _error(str(exc))


@app.post("/workspace/write")
async def workspace_write(req: WriteRequest) -> dict:
    try:
        workdir = _resolve_rel_dir(req.rel_dir)
        async with _workspace_locks[req.rel_dir]:
            target = _resolve_path(workdir, req.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(req.content, encoding="utf-8")
            return {"path": req.path, "size": target.stat().st_size,
                    "changed_files": [{"path": req.path, "size": target.stat().st_size}]}
    except (ValueError, OSError) as exc:
        return _error(str(exc))


@app.post("/workspace/edit")
async def workspace_edit(req: EditRequest) -> dict:
    try:
        workdir = _resolve_rel_dir(req.rel_dir)
        async with _workspace_locks[req.rel_dir]:
            target = _resolve_path(workdir, req.path)
            if not target.is_file():
                return _error(f"文件不存在: {req.path}")
            try:
                text = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return _error("二进制文件不支持 ws_edit")
            count = text.count(req.old)
            if count == 0:
                return _error("未找到 old 字符串")
            if count > 1 and not req.replace_all:
                return _error(f"old 字符串出现 {count} 次，请加 replace_all=true 或提供更具体的上下文")
            updated = text.replace(req.old, req.new) if req.replace_all else text.replace(req.old, req.new, 1)
            old_size = target.stat().st_size
            new_size = len(updated.encode("utf-8"))
            if req.dry_run:
                return {"path": req.path, "replaced": count if req.replace_all else 1,
                        "old_size": old_size, "size": new_size}
            target.write_text(updated, encoding="utf-8")
            return {"path": req.path, "replaced": count if req.replace_all else 1,
                    "old_size": old_size, "size": new_size,
                    "changed_files": [{"path": req.path, "size": new_size}]}
    except (ValueError, OSError) as exc:
        return _error(str(exc))


@app.post("/workspace/delete")
async def workspace_delete(req: DeleteRequest) -> dict:
    try:
        workdir = _resolve_rel_dir(req.rel_dir)
        async with _workspace_locks[req.rel_dir]:
            target = _resolve_path(workdir, req.path)
            if not target.exists():
                return _error(f"文件不存在: {req.path}")
            if target.is_dir():
                return _error("不允许通过 ws_delete 删目录")
            target.unlink()
            return {"deleted": req.path}
    except (ValueError, OSError) as exc:
        return _error(str(exc))


@app.post("/workspace/stat")
async def workspace_stat(req: StatRequest) -> dict:
    try:
        workdir = _resolve_rel_dir(req.rel_dir)
        async with _workspace_locks[req.rel_dir]:
            target = _resolve_path(workdir, req.path)
            if not target.is_file():
                return _error(f"文件不存在: {req.path}")
            return {"path": req.path, "size": target.stat().st_size}
    except (ValueError, OSError) as exc:
        return _error(str(exc))
