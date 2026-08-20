"""Unified per-session workspace runtime.

All agent workspace mutations and code execution enter through this service.  The
backend owns authorization, quotas, and ChatFile records; this process owns the
filesystem boundary and serializes operations for one session.
"""
import asyncio
import json
import logging
import os
import signal
import shlex
import shutil
import subprocess
import tempfile
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import sandbox_runner

app = FastAPI(title="code-sandbox", docs_url=None, redoc_url=None)
logger = logging.getLogger("sandbox.runtime")

WORKSPACES_ROOT = Path(os.environ.get("WORKSPACES_ROOT", "/workspaces")).resolve()
SYSTEM_SKILLS_ROOT = Path(os.environ.get("SYSTEM_SKILLS_ROOT", "/skill-packages/system")).resolve()
USER_SKILLS_ROOT = Path(os.environ.get("USER_SKILLS_ROOT", "/skill-packages/user")).resolve()
EXEC_TIMEOUT = int(os.environ.get("SANDBOX_EXEC_TIMEOUT", "30"))
MAX_OUTPUT_BYTES = int(os.environ.get("SANDBOX_MAX_OUTPUT_BYTES", str(256 * 1024)))
_exec_semaphore = asyncio.Semaphore(int(os.environ.get("SANDBOX_CONCURRENCY", "1")))
_workspace_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_skill_root_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class SkillMount(BaseModel):
    skill_id: int
    source_type: Literal["system", "user"]
    user_id: Optional[int] = None
    package_path: str
    read_only: bool = True


class SkillRootMount(BaseModel):
    scope: Literal["system", "user"]
    user_id: Optional[int] = None
    read_only: bool = True


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
    skill_mounts: list["SkillMount"] = Field(default_factory=list)
    skill_roots: list["SkillRootMount"] = Field(default_factory=list)
    skill_id: Optional[int] = None
    skill_script_path: Optional[str] = None
    skill_script_args: list[str] = Field(default_factory=list)
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


def _resolve_cwd(workdir: Path, cwd: Optional[str]) -> str:
    """Validate cwd and return its in-namespace absolute path."""
    raw = (cwd or "").strip().replace("\\", "/")
    if not raw or raw == ".":
        return "/workspace"
    parts = [part for part in raw.split("/") if part]
    if ".." in parts:
        raise ValueError("cwd 不允许包含 ..")
    if raw.startswith("/"):
        allowed = (
            raw == "/" or raw == "/workspace" or raw.startswith("/workspace/")
            or raw == "/skills/system" or raw.startswith("/skills/system/")
            or raw == "/skills/user" or raw.startswith("/skills/user/")
        )
        if not allowed:
            raise ValueError("cwd 绝对路径不在允许范围内")
        return raw.rstrip("/") or "/"
    _resolve_path(workdir, raw)
    return "/workspace/" + raw


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


def _snapshot_mounts(mounts: list[tuple[Path, Path, bool]]) -> dict[tuple[str, str], tuple[int, int]]:
    snapshot: dict[tuple[str, str], tuple[int, int]] = {}
    for source, destination, _ in mounts:
        for entry in source.rglob("*"):
            if entry.is_file() and not entry.is_symlink():
                try:
                    stat = entry.stat()
                    snapshot[(str(destination), entry.relative_to(source).as_posix())] = (
                        stat.st_size, stat.st_mtime_ns
                    )
                except OSError:
                    continue
    return snapshot


def _mount_changes(mounts: list[tuple[Path, Path, bool]], before: dict[tuple[str, str], tuple[int, int]]) -> list[dict]:
    after = _snapshot_mounts(mounts)
    changed = [
        {"mount_path": key[0], "path": key[1], "size": metadata[0]}
        for key, metadata in after.items() if before.get(key) != metadata
    ]
    changed.extend(
        {"mount_path": key[0], "path": key[1], "deleted": True}
        for key in before if key not in after
    )
    return sorted(changed, key=lambda item: (item["mount_path"], item["path"]))


def _resolve_skill_roots(roots: list[SkillRootMount]) -> list[tuple[Path, Path, bool, str]]:
    resolved: list[tuple[Path, Path, bool, str]] = []
    seen: set[str] = set()
    for mount in roots:
        if mount.scope in seen:
            raise ValueError("重复 Skill root mount")
        seen.add(mount.scope)
        if mount.scope == "system":
            source = SYSTEM_SKILLS_ROOT
            destination = Path("/skills/system")
            read_only = True
        else:
            if mount.user_id is None or mount.user_id <= 0:
                raise ValueError("用户 Skill root mount 缺少有效 user_id")
            source = (USER_SKILLS_ROOT / str(mount.user_id)).resolve()
            if source.parent != USER_SKILLS_ROOT:
                raise ValueError("Skill user root path 非法")
            source.mkdir(parents=True, exist_ok=True)
            destination = Path("/skills/user")
            read_only = False
        source = source.resolve()
        if not source.exists() or not source.is_dir():
            raise ValueError("Skill root 不存在或不是目录")
        resolved.append((source, destination, read_only, mount.scope))
    return resolved


def _snapshot_skill_roots(
    roots: list[tuple[Path, Path, bool, str]],
) -> dict[tuple[str, str], tuple[int, int]]:
    snapshot: dict[tuple[str, str], tuple[int, int]] = {}
    for source, _, _, scope in roots:
        for entry in source.rglob("*"):
            if entry.is_symlink() or not entry.is_file():
                continue
            try:
                relative = entry.relative_to(source).as_posix()
                stat = entry.stat()
                snapshot[(scope, relative)] = (stat.st_size, stat.st_mtime_ns)
            except OSError:
                continue
    return snapshot


def _skill_root_changes(
    roots: list[tuple[Path, Path, bool, str]],
    before: dict[tuple[str, str], tuple[int, int]],
) -> list[dict]:
    after = _snapshot_skill_roots(roots)
    changed = [
        {
            "scope": key[0],
            "package_path": key[1].split("/", 1)[0],
            "path": key[1].split("/", 1)[1] if "/" in key[1] else "",
            "size": metadata[0],
        }
        for key, metadata in after.items()
        if before.get(key) != metadata
    ]
    changed.extend(
        {
            "scope": key[0],
            "package_path": key[1].split("/", 1)[0],
            "path": key[1].split("/", 1)[1] if "/" in key[1] else "",
            "deleted": True,
        }
        for key in before
        if key not in after
    )
    return sorted(changed, key=lambda item: (item["scope"], item["package_path"], item["path"]))


def _snapshot_size(snapshot: dict[tuple[str, str], tuple[int, int]], scope: Optional[str] = None) -> int:
    return sum(
        metadata[0]
        for (current_scope, _), metadata in snapshot.items()
        if scope is None or current_scope == scope
    )


def _reject_skill_root_symlinks(roots: list[tuple[Path, Path, bool, str]]) -> None:
    for source, _, _, scope in roots:
        if scope != "user":
            continue
        for entry in source.rglob("*"):
            if entry.is_symlink():
                raise ValueError(f"用户 Skill 目录不允许符号链接: {entry.name}")


def _stage_skill_roots(
    roots: list[tuple[Path, Path, bool, str]],
) -> tuple[list[tuple[Path, Path, bool, str]], list[Path]]:
    """Copy writable user roots so quota failures cannot mutate the volume."""
    staged: list[tuple[Path, Path, bool, str]] = []
    temporary_roots: list[Path] = []
    for source, destination, read_only, scope in roots:
        if scope != "user" or read_only:
            staged.append((source, destination, read_only, scope))
            continue
        stage = Path(tempfile.mkdtemp(prefix=f".exec-{source.name}-", dir=str(source.parent)))
        shutil.copytree(source, stage, dirs_exist_ok=True, symlinks=True)
        staged.append((stage, destination, False, scope))
        temporary_roots.append(stage)
    return staged, temporary_roots


def _commit_staged_skill_root(stage: Path, target: Path, *, preserve_backup: bool = False) -> Optional[Path]:
    backup = target.with_name(target.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    os.replace(target, backup)
    try:
        os.replace(stage, target)
    except OSError:
        if backup.exists() and not target.exists():
            os.replace(backup, target)
        raise
    else:
        if not preserve_backup:
            shutil.rmtree(backup, ignore_errors=True)
        return backup if preserve_backup else None


def _commit_staged_skill_roots(
    original: list[tuple[Path, Path, bool, str]],
    staged: list[tuple[Path, Path, bool, str]],
) -> list[tuple[Path, Path]]:
    backups: list[tuple[Path, Path]] = []
    for source, _, read_only, scope in original:
        if scope != "user" or read_only:
            continue
        staged_source = next(
            item[0]
            for item in staged
            if item[3] == scope and item[1] == Path("/skills/user")
        )
        try:
            backup = _commit_staged_skill_root(staged_source, source, preserve_backup=True)
        except OSError:
            _rollback_skill_root_commits(backups)
            raise
        if backup is not None:
            backups.append((source, backup))
    return backups


def _rollback_skill_root_commits(backups: list[tuple[Path, Path]]) -> None:
    for target, backup in reversed(backups):
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if backup.exists():
            os.replace(backup, target)


def _discard_skill_root_backups(backups: list[tuple[Path, Path]]) -> None:
    for _, backup in backups:
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)


def _dir_size_bytes(path: Path) -> int:
    return sum(metadata[0] for metadata in _snapshot(path).values())


def _validate_exec_quota(
    stage: Path,
    workdir: Path,
    req: ExecRequest,
    skill_roots: list[tuple[Path, Path, bool, str]] | None = None,
    skill_before: dict[tuple[str, str], tuple[int, int]] | None = None,
) -> Optional[str]:
    staged = _snapshot(stage)
    skill_after = _snapshot_skill_roots(skill_roots or [])
    skill_before = skill_before or {}
    changed_skill_sizes = [
        size
        for key, (size, _) in skill_after.items()
        if size > 0 and skill_before.get(key) != skill_after[key]
    ]
    oversized = next(
        (size for size, _ in staged.values() if size > req.max_file_bytes),
        next((size for size in changed_skill_sizes if size > req.max_file_bytes), None),
    )
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
    user_size = (
        _dir_size_bytes(user_root)
        - _dir_size_bytes(workdir)
        + staged_size
        + _snapshot_size(skill_after, "user")
    )
    if user_size > req.max_user_bytes:
        return f"用户配额超限：{user_size / 1024 / 1024:.1f}MB"
    return None


@asynccontextmanager
async def _skill_root_lock(req: ExecRequest):
    user_ids = {
        mount.user_id
        for mount in req.skill_roots
        if mount.scope == "user" and mount.user_id is not None
    }
    if not user_ids:
        yield
        return
    if len(user_ids) > 1:
        raise ValueError("一次执行只能挂载一个用户 Skill 根目录")
    lock = _skill_root_locks[str(next(iter(user_ids)))]
    async with lock:
        yield


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


def _resolve_skill_mounts(mounts: list[SkillMount]) -> list[tuple[Path, Path, bool]]:
    resolved: list[tuple[Path, Path, bool]] = []
    seen: set[int] = set()
    for mount in mounts:
        if mount.skill_id in seen:
            raise ValueError("重复 Skill mount")
        seen.add(mount.skill_id)
        if mount.source_type == "system":
            root = SYSTEM_SKILLS_ROOT
        else:
            if mount.user_id is None or mount.user_id <= 0:
                raise ValueError("用户 Skill mount 缺少有效 user_id")
            root = (USER_SKILLS_ROOT / str(mount.user_id)).resolve()
            if root.parent != USER_SKILLS_ROOT:
                raise ValueError("Skill user path 非法")
        rel = Path(mount.package_path.replace("\\", "/"))
        if (not mount.package_path or rel.is_absolute() or ".." in rel.parts
                or len(rel.parts) != 1 or rel.name in {".", ".."}):
            raise ValueError("Skill package path 非法")
        source = (root / rel).resolve()
        if source == root or root not in source.parents or source.is_symlink() or not source.is_dir():
            raise ValueError("Skill package 不存在或越界")
        destination = Path("/skills") / mount.source_type / mount.package_path
        # The source type is authoritative: a caller cannot make a system
        # package writable by setting read_only=false in the request.
        resolved.append((source, destination, mount.source_type == "system"))
    return resolved


def _bwrap_command(workdir: Path, meta_dir: Optional[Path] = None,
                   skill_mounts: list[tuple[Path, Path, bool]] | None = None,
                   skill_roots: list[tuple[Path, Path, bool, str]] | None = None) -> list[str]:
    command = [
        "bwrap", "--die-with-parent", "--new-session", "--unshare-user", "--uid", "0", "--gid", "0",
        "--unshare-pid", "--unshare-net", "--clearenv",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/usr/local", "/usr/local",
        "--ro-bind", "/bin", "/bin", "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64", "--ro-bind", "/etc", "/etc",
        # A nested proc mount is blocked by this host's non-privileged Docker
        # policy. The sandbox does not need procfs for code execution.
        "--dev", "/dev", "--tmpfs", "/tmp",
        "--dir", "/skills", "--bind", str(workdir), "/workspace", "--chdir", "/workspace",
        "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
        "--setenv", "HOME", "/tmp", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
    ]
    for source, destination, read_only in skill_mounts or []:
        command += ["--ro-bind" if read_only else "--bind", str(source), str(destination)]
    for source, destination, read_only, _ in skill_roots or []:
        command += ["--ro-bind" if read_only else "--bind", str(source), str(destination)]
    read_roots = [str(destination) for _, destination, _ in (skill_mounts or [])]
    read_roots.extend(str(destination) for _, destination, _, _ in (skill_roots or []))
    writable_roots = [
        str(destination)
        for _, destination, read_only in (skill_mounts or [])
        if not read_only
    ]
    writable_roots.extend(
        str(destination) for _, destination, read_only, _ in (skill_roots or []) if not read_only
    )
    if read_roots:
        command += ["--setenv", "SANDBOX_READ_ROOTS", os.pathsep.join(read_roots)]
        command += ["--setenv", "SANDBOX_WRITE_ROOTS", os.pathsep.join(writable_roots)]
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


def _run_bash(command: str, workdir: Path, cwd: Optional[str], timeout: int,
              skill_mounts: list[tuple[Path, Path, bool]] | None = None,
              skill_roots: list[tuple[Path, Path, bool, str]] | None = None) -> dict:
    if not command:
        return _error("bash 需要 command", stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])
    try:
        shell_cwd = _resolve_cwd(workdir, cwd)
        shell_prefix = f"cd -- {shlex.quote(shell_cwd)} && "
        before = _snapshot(workdir)
        process = subprocess.Popen(
            _bwrap_command(workdir, skill_mounts=skill_mounts or [], skill_roots=skill_roots or [])
            + ["--", "/bin/bash", "-lc", shell_prefix + command],
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
        skill_mounts = _resolve_skill_mounts(req.skill_mounts)
        if req.skill_script_path:
            mount_request = next((item for item in req.skill_mounts if item.skill_id == req.skill_id), None)
            mount = next((item for item in skill_mounts if mount_request and item[1] == Path("/skills") / mount_request.source_type / mount_request.package_path), None)
            if mount is None:
                raise ValueError("Skill script 未绑定")
            relative = Path(req.skill_script_path.replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Skill script 路径非法")
            script = (mount[0] / relative).resolve()
            if mount[0] not in script.parents or not script.is_file():
                raise ValueError("Skill script 不存在或越界")
        else:
            script = _resolve_path(workdir, req.script_path) if req.script_path else None
    except ValueError as exc:
        return _error(str(exc), stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])

    def builder(meta_dir: Path, runner: Path, user_code: Path, _workdir: Path) -> list[str]:
        if req.skill_script_path:
            inside_code = str(mount[1]) + "/" + req.skill_script_path.replace("\\", "/")
        else:
            inside_code = "/workspace/" + req.script_path.replace("\\", "/") if req.script_path else "/meta/user_code.py"
        return _bwrap_command(workdir, meta_dir, skill_mounts) + [
            "--setenv", "SANDBOX_USER_CODE", inside_code,
            "--setenv", "SANDBOX_OUTPUT_DIR", "/workspace",
            "--setenv", "SANDBOX_SCRIPT_ARGS", json.dumps(req.skill_script_args),
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
    user_skill_ids = {
        mount.user_id
        for mount in req.skill_roots
        if mount.scope == "user" and mount.user_id is not None
    }
    if len(user_skill_ids) > 1:
        return _error("一次执行只能挂载一个用户 Skill 根目录", stdout="", stderr="", exit_code=-1, produced=[], changed_files=[])
    timeout = max(1, min(req.timeout, 120))
    async with _workspace_locks[req.rel_dir]:
        async with _exec_semaphore:
            async with _skill_root_lock(req):
                loop = asyncio.get_running_loop()
                stage = await loop.run_in_executor(None, _stage_workspace, workdir)
                temporary_skill_roots: list[Path] = []
                try:
                    mounts = _resolve_skill_mounts(req.skill_mounts)
                    roots = _resolve_skill_roots(req.skill_roots)
                    staged_roots, temporary_skill_roots = await loop.run_in_executor(
                        None, _stage_skill_roots, roots
                    )
                    mount_before = _snapshot_mounts(mounts)
                    root_before = _snapshot_skill_roots(roots)
                    if req.runtime == "bash":
                        if mounts or staged_roots:
                            result = await loop.run_in_executor(
                                None, _run_bash, req.command or "", stage, req.cwd, timeout, mounts, staged_roots
                            )
                        else:
                            # Preserve the four-argument hook used by existing tests
                            # and local integrations that monkeypatch the runner.
                            result = await loop.run_in_executor(None, _run_bash, req.command or "", stage, req.cwd, timeout)
                    else:
                        result = await loop.run_in_executor(None, _run_python, req, stage, timeout)
                    if result.get("error") or result.get("exit_code", 0) != 0:
                        logger.warning(
                            "execution completed with failure rel_dir=%s runtime=%s cwd=%r exit_code=%s error=%s stderr=%s",
                            req.rel_dir, req.runtime, req.cwd,
                            result.get("exit_code"), result.get("error"), result.get("stderr", "")[:500],
                        )
                    if result.get("error"):
                        return result
                    try:
                        await loop.run_in_executor(None, _reject_skill_root_symlinks, staged_roots)
                    except ValueError as exc:
                        return _error(str(exc), stdout=result.get("stdout", ""), stderr=result.get("stderr", ""),
                                      exit_code=result.get("exit_code", -1), produced=[], changed_files=[], deleted_files=[])
                    quota_error = await loop.run_in_executor(
                        None, _validate_exec_quota, stage, workdir, req, staged_roots, root_before
                    )
                    if quota_error:
                        return _error(quota_error, stdout=result.get("stdout", ""), stderr=result.get("stderr", ""),
                                      exit_code=result.get("exit_code", -1), produced=[], changed_files=[], deleted_files=[])
                    skill_backups = await loop.run_in_executor(
                        None, lambda: _commit_staged_skill_roots(roots, staged_roots)
                    ) or []
                    try:
                        await loop.run_in_executor(None, _commit_staged_workspace, stage, workdir)
                    except BaseException:
                        await loop.run_in_executor(None, _rollback_skill_root_commits, skill_backups)
                        raise
                    await loop.run_in_executor(None, _discard_skill_root_backups, skill_backups)
                    result["skill_changed_files"] = _mount_changes(mounts, mount_before)
                    result["skill_changed_files"].extend(_skill_root_changes(roots, root_before))
                    return result
                finally:
                    if stage.exists():
                        await loop.run_in_executor(None, shutil.rmtree, stage, True)
                    for temporary_root in temporary_skill_roots:
                        if temporary_root.exists():
                            await loop.run_in_executor(None, shutil.rmtree, temporary_root, True)


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
