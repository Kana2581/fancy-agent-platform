"""Unit tests for PythonExecTool's unified workspace-execution path.

After the sandbox/workspace unification, code runs with cwd = the session workspace.
Files produced by the code are registered as `storage_type="workspace"` ChatFile rows
(showing up in the workspace panel); image products are additionally published to
UPLOAD_DIR/generated/ with a public URL so chat inline-preview still works.

These tests exercise the **local** execution path (settings.SANDBOX_EXEC_URL == "")
which runs the real subprocess sandbox via app.utils.sandbox_runner — fast for trivial code.
"""
from pathlib import Path

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.models.chat_file import ChatFile  # noqa: F401  ensure table is registered
from app.utils.langchain.builtin_tools.python_exec import (
    PythonExecTool,
    build_python_exec_tool,
)


@pytest_asyncio.fixture
async def patched_session_factory(async_engine, monkeypatch):
    """Point both the source and the re-exported `async_session_factory` at the in-memory
    test engine so `get_db_session()` (called inside _register_workspace_file) writes through
    to our fixture. Patching only the source module is not enough once `app.deps.db` has been
    imported earlier in the test run — Python binds the name at import time.
    """
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    monkeypatch.setattr("app.core.database.async_session_factory", factory)

    import app.deps.db as deps_db
    monkeypatch.setattr(deps_db, "async_session_factory", factory)

    yield factory


@pytest_asyncio.fixture
def workspace_env(tmp_path, monkeypatch):
    """Force local subprocess execution into a tmp workspace + tmp uploads dir."""
    monkeypatch.setattr(settings, "SANDBOX_EXEC_URL", "")
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path / "workspaces"))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "OSS_URL", "http://test-oss")
    return tmp_path


async def test_code_products_register_as_workspace_files(
    workspace_env, async_engine, async_session, patched_session_factory
):
    tool = PythonExecTool(user_id=42, session_id="sess-abc")
    code = (
        "open('report.txt', 'w', encoding='utf-8').write('hello')\n"
        "open('chart.png', 'wb').write(b'\\x89PNG\\r\\n\\x1a\\nfake')\n"
        "print('done')\n"
    )
    raw = await tool._arun(code)

    import json
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert "done" in payload["stdout"]

    # Both products surfaced; each carries a workspace file_id
    by_name = {Path(f["path"]).name: f for f in payload["files"]}
    assert set(by_name) == {"report.txt", "chart.png"}
    assert all("file_id" in f and f["file_id"] is not None for f in payload["files"])

    # Image gets a public generated URL for inline preview; the text file does not
    assert by_name["chart.png"]["url"].startswith("http://test-oss/generated/")
    assert "url" not in by_name["report.txt"]

    # The published image physically exists under uploads/generated/
    gen_root = Path(settings.UPLOAD_DIR) / "generated"
    assert any(gen_root.rglob("*.png"))

    # DB rows: both registered as workspace, scoped to the session/user
    rows = (await async_session.execute(select(ChatFile))).scalars().all()
    assert {r.storage_type for r in rows} == {"workspace"}
    assert {r.session_id for r in rows} == {"sess-abc"}
    assert {r.upload_user_id for r in rows} == {42}
    assert {r.file_ext for r in rows} == {"txt", "png"}

    # The products live in the session workspace (cwd), proving unification
    ws = Path(settings.WORKSPACE_DIR) / "42" / "sess-abc"
    assert (ws / "report.txt").read_text(encoding="utf-8") == "hello"


async def test_code_can_read_preexisting_workspace_file(
    workspace_env, async_engine, async_session, patched_session_factory
):
    # Seed a file as if ws_write had created it
    ws = Path(settings.WORKSPACE_DIR) / "7" / "sess-read"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "input.txt").write_text("source-data", encoding="utf-8")

    tool = PythonExecTool(user_id=7, session_id="sess-read")
    code = "print(open('input.txt').read().upper())"
    import json
    payload = json.loads(await tool._arun(code))

    assert payload["exit_code"] == 0
    assert "SOURCE-DATA" in payload["stdout"]
    # Reading didn't fabricate a product
    assert payload["files"] == []


def test_run_without_session_degrades_to_scratch(workspace_env):
    """No user/session -> scratch tmp dir, no persistence, filenames only."""
    import json
    tool = PythonExecTool()
    payload = json.loads(tool._run("open('x.txt','w').write('a'); print('ok')"))
    assert payload["exit_code"] == 0
    assert "ok" in payload["stdout"]
    assert [f["filename"] for f in payload["files"]] == ["x.txt"]
    assert all("file_id" not in f for f in payload["files"])


def test_builder_propagates_user_and_session_ids():
    tool = build_python_exec_tool(user_id=7, session_id="sess-xyz")
    assert isinstance(tool, PythonExecTool)
    assert tool.user_id == 7
    assert tool.session_id == "sess-xyz"


def test_builder_defaults_to_none():
    tool = build_python_exec_tool()
    assert isinstance(tool, PythonExecTool)
    assert tool.user_id is None
    assert tool.session_id is None
