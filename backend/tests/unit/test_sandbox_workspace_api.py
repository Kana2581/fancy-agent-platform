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
