"""Contract tests for the sandbox-owned workspace filesystem API."""
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

SANDBOX_DIR = Path(__file__).resolve().parents[3] / "sandbox"
RUNNER_DIR = Path(__file__).resolve().parents[2] / "app" / "utils"
if str(SANDBOX_DIR) not in sys.path:
    sys.path.insert(0, str(SANDBOX_DIR))
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))
import server as sandbox_server  # noqa: E402


@pytest.fixture
def sandbox_root(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox_server, "WORKSPACES_ROOT", tmp_path / "workspaces")
    return tmp_path / "workspaces"


async def _post(path: str, payload: dict):
    transport = ASGITransport(app=sandbox_server.app)
    async with AsyncClient(transport=transport, base_url="http://sandbox") as client:
        response = await client.post(path, json=payload)
    assert response.status_code == 200
    return response.json()


async def test_workspace_api_read_write_edit_list_delete(sandbox_root):
    base = {"rel_dir": "12/session-a"}
    written = await _post("/workspace/write", {**base, "path": "notes/a.txt", "content": "one\ntwo"})
    assert written["changed_files"] == [{"path": "notes/a.txt", "size": 8}]

    listed = await _post("/workspace/list", {**base, "path": "notes"})
    assert listed["entries"] == [{"name": "a.txt", "type": "file", "size": 8}]

    read = await _post("/workspace/read", {**base, "path": "notes/a.txt", "offset": 0, "limit": 20})
    assert read["content"] == "one\ntwo"

    edited = await _post("/workspace/edit", {**base, "path": "notes/a.txt", "old": "two", "new": "three"})
    assert edited["replaced"] == 1

    deleted = await _post("/workspace/delete", {**base, "path": "notes/a.txt"})
    assert deleted == {"deleted": "notes/a.txt"}


async def test_exec_rejects_over_quota_output_without_persisting_it(sandbox_root, monkeypatch):
    monkeypatch.setattr(sandbox_server, "_bwrap_healthy", lambda: True)

    def write_large_file(_command, workdir, _cwd, _timeout):
        (workdir / "too-large.txt").write_bytes(b"12345")
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": 0,
            "produced": ["too-large.txt"],
            "changed_files": [{"path": "too-large.txt", "size": 5}],
            "deleted_files": [],
        }

    monkeypatch.setattr(sandbox_server, "_run_bash", write_large_file)
    result = await _post("/exec", {
        "runtime": "bash",
        "rel_dir": "12/session-a",
        "command": "ignored",
        "max_file_bytes": 4,
        "max_session_bytes": 10,
        "max_user_bytes": 10,
        "max_files": 10,
    })

    assert "单文件超限" in result["error"]
    assert result["changed_files"] == []
    assert not (sandbox_root / "12" / "session-a" / "too-large.txt").exists()


async def test_exec_rejects_over_user_quota_skill_output_without_persisting_it(sandbox_root, tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox_server, "_bwrap_healthy", lambda: True)
    user_skills_root = tmp_path / "skill-packages" / "user"
    monkeypatch.setattr(sandbox_server, "USER_SKILLS_ROOT", user_skills_root.resolve())

    def write_skill_file(_command, _workdir, _cwd, _timeout, _mounts, skill_roots):
        user_root = next(source for source, _, _, scope in skill_roots if scope == "user")
        package = user_root / "generated"
        package.mkdir(parents=True, exist_ok=True)
        (package / "output.bin").write_bytes(b"12345")
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": 0,
            "produced": [],
            "changed_files": [],
            "deleted_files": [],
        }

    monkeypatch.setattr(sandbox_server, "_run_bash", write_skill_file)
    result = await _post("/exec", {
        "runtime": "bash",
        "rel_dir": "12/session-a",
        "command": "ignored",
        "max_file_bytes": 100,
        "max_session_bytes": 100,
        "max_user_bytes": 4,
        "max_files": 10,
        "skill_roots": [{"scope": "user", "user_id": 12, "read_only": False}],
    })

    assert "用户配额超限" in result["error"]
    assert not (user_skills_root / "12" / "generated" / "output.bin").exists()


async def test_exec_does_not_count_skill_bytes_toward_session_quota(sandbox_root, tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox_server, "_bwrap_healthy", lambda: True)
    user_skills_root = tmp_path / "skill-packages" / "user"
    monkeypatch.setattr(sandbox_server, "USER_SKILLS_ROOT", user_skills_root.resolve())

    def write_skill_file(_command, workdir, _cwd, _timeout, _mounts, skill_roots):
        (workdir / "workspace.txt").write_bytes(b"1234")
        user_root = next(source for source, _, _, scope in skill_roots if scope == "user")
        package = user_root / "generated"
        package.mkdir(parents=True, exist_ok=True)
        (package / "skill.txt").write_bytes(b"56789")
        return {"stdout": "", "stderr": "", "exit_code": 0, "produced": [], "changed_files": [], "deleted_files": []}

    monkeypatch.setattr(sandbox_server, "_run_bash", write_skill_file)
    result = await _post("/exec", {
        "runtime": "bash",
        "rel_dir": "12/session-a",
        "command": "ignored",
        "max_file_bytes": 100,
        "max_session_bytes": 4,
        "max_user_bytes": 100,
        "max_files": 10,
        "skill_roots": [{"scope": "user", "user_id": 12, "read_only": False}],
    })

    assert "error" not in result
    assert (sandbox_root / "12" / "session-a" / "workspace.txt").read_bytes() == b"1234"
    assert (user_skills_root / "12" / "generated" / "skill.txt").read_bytes() == b"56789"


async def test_exec_rolls_back_skill_when_workspace_commit_fails(sandbox_root, tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox_server, "_bwrap_healthy", lambda: True)
    user_skills_root = tmp_path / "skill-packages" / "user"
    monkeypatch.setattr(sandbox_server, "USER_SKILLS_ROOT", user_skills_root.resolve())

    def write_skill_file(_command, workdir, _cwd, _timeout, _mounts, skill_roots):
        (workdir / "workspace.txt").write_text("new", encoding="utf-8")
        user_root = next(source for source, _, _, scope in skill_roots if scope == "user")
        package = user_root / "generated"
        package.mkdir(parents=True, exist_ok=True)
        (package / "skill.txt").write_text("new", encoding="utf-8")
        return {"stdout": "", "stderr": "", "exit_code": 0, "produced": [], "changed_files": [], "deleted_files": []}

    def fail_workspace_commit(_stage, _workdir):
        raise OSError("workspace commit failed")

    monkeypatch.setattr(sandbox_server, "_run_bash", write_skill_file)
    monkeypatch.setattr(sandbox_server, "_commit_staged_workspace", fail_workspace_commit)
    request = sandbox_server.ExecRequest(
        runtime="bash",
        rel_dir="12/session-a",
        command="ignored",
        max_file_bytes=100,
        max_session_bytes=100,
        max_user_bytes=100,
        max_files=10,
        skill_roots=[{"scope": "user", "user_id": 12, "read_only": False}],
    )

    with pytest.raises(OSError, match="workspace commit failed"):
        await sandbox_server.exec_code(request)
    assert not (sandbox_root / "12" / "session-a" / "workspace.txt").exists()
    assert not (user_skills_root / "12" / "generated" / "skill.txt").exists()


async def test_exec_commits_valid_user_skill_output(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox_server, "_bwrap_healthy", lambda: True)
    user_skills_root = tmp_path / "skill-packages" / "user"
    monkeypatch.setattr(sandbox_server, "USER_SKILLS_ROOT", user_skills_root.resolve())

    def write_skill_file(_command, _workdir, _cwd, _timeout, _mounts, skill_roots):
        user_root = next(source for source, _, _, scope in skill_roots if scope == "user")
        package = user_root / "generated"
        package.mkdir(parents=True, exist_ok=True)
        (package / "SKILL.md").write_text("---\nname: generated\ndescription: test\n---\n", encoding="utf-8")
        return {"stdout": "", "stderr": "", "exit_code": 0, "produced": [], "changed_files": [], "deleted_files": []}

    monkeypatch.setattr(sandbox_server, "_run_bash", write_skill_file)
    result = await _post("/exec", {
        "runtime": "bash",
        "rel_dir": "12/session-a",
        "command": "ignored",
        "max_file_bytes": 1000,
        "max_session_bytes": 1000,
        "max_user_bytes": 1000,
        "max_files": 10,
        "skill_roots": [{"scope": "user", "user_id": 12, "read_only": False}],
    })

    assert result["skill_changed_files"] == [{
        "scope": "user",
        "package_path": "generated",
        "path": "SKILL.md",
        "size": 46,
    }]
    assert (user_skills_root / "12" / "generated" / "SKILL.md").is_file()


async def test_exec_counts_existing_user_skill_bytes_toward_user_quota(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox_server, "_bwrap_healthy", lambda: True)
    user_skills_root = tmp_path / "skill-packages" / "user"
    existing_root = user_skills_root / "12" / "existing"
    existing_root.mkdir(parents=True)
    (existing_root / "data.txt").write_bytes(b"1234")
    monkeypatch.setattr(sandbox_server, "USER_SKILLS_ROOT", user_skills_root.resolve())

    def write_skill_file(_command, _workdir, _cwd, _timeout, _mounts, skill_roots):
        user_root = next(source for source, _, _, scope in skill_roots if scope == "user")
        package = user_root / "generated"
        package.mkdir(parents=True, exist_ok=True)
        (package / "data.txt").write_bytes(b"x")
        return {"stdout": "", "stderr": "", "exit_code": 0, "produced": [], "changed_files": [], "deleted_files": []}

    monkeypatch.setattr(sandbox_server, "_run_bash", write_skill_file)
    result = await _post("/exec", {
        "runtime": "bash",
        "rel_dir": "12/session-a",
        "command": "ignored",
        "max_file_bytes": 1000,
        "max_session_bytes": 1000,
        "max_user_bytes": 4,
        "max_files": 10,
        "skill_roots": [{"scope": "user", "user_id": 12, "read_only": False}],
    })

    assert "用户配额超限" in result["error"]
    assert not (user_skills_root / "12" / "generated" / "data.txt").exists()


async def test_workspace_edit_dry_run_handles_content_larger_than_read_limit(sandbox_root):
    base = {"rel_dir": "12/session-a", "path": "large.txt"}
    content = "a" * 20_000 + "target" + "z" * 20_000
    await _post("/workspace/write", {**base, "content": content})

    preview = await _post("/workspace/edit", {
        **base, "old": "target", "new": "updated", "dry_run": True,
    })

    assert preview["replaced"] == 1
    assert preview["old_size"] == len(content.encode("utf-8"))
    assert preview["size"] == len(content.replace("target", "updated").encode("utf-8"))
    unchanged = await _post("/workspace/read", {**base, "offset": 19_995, "limit": 20})
    assert unchanged["content"] == "aaaaatargetzzzzzzzzz"


@pytest.mark.parametrize("path", ["../outside.txt", "/etc/passwd", "C:\\outside.txt"])
async def test_workspace_api_rejects_escape_paths(sandbox_root, path):
    response = await _post("/workspace/write", {"rel_dir": "12/session-a", "path": path, "content": "x"})
    assert "error" in response


async def test_workspace_api_rejects_symlinks(sandbox_root):
    root = sandbox_root / "12" / "session-a"
    root.mkdir(parents=True)
    outside = sandbox_root / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    try:
        (root / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows test host")
    response = await _post("/workspace/read", {"rel_dir": "12/session-a", "path": "link.txt"})
    assert "error" in response
