"""Skill 升级（带可执行脚本的能力包）测试。

覆盖：
- SkillService.create_skill(files=...) 落 skill_files 行；删 skill 级联删文件
- 文件校验：越界 path / 超 caps 抛 ValueError
- use_skill 工具：物化到工作区 .skills/<name>/、返回清单、不产生 ChatFile 行
- python_exec(script=...)：运行工作区脚本，产物登记为 workspace 文件
- 安全回归：脚本里 import os 被白名单拦
"""
import json
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.models.chat_file import ChatFile  # noqa: F401
from app.models.skill_file import SkillFile
from app.services.skill_service import SkillService, validate_skill_files
from app.utils.langchain.builtin_tools.python_exec import PythonExecTool
from app.utils.langchain.builtin_tools.skill_manager_tool import build_skill_manager_tools


@pytest_asyncio.fixture
async def patched_session_factory(async_engine, monkeypatch):
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    monkeypatch.setattr("app.core.database.async_session_factory", factory)
    import app.deps.db as deps_db
    monkeypatch.setattr(deps_db, "async_session_factory", factory)
    yield factory


@pytest_asyncio.fixture
def workspace_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SANDBOX_EXEC_URL", "")
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path / "workspaces"))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "OSS_URL", "http://test-oss")
    return tmp_path


def _use_skill_tool(user_id, session_id):
    tools = build_skill_manager_tools(user_id, session_id=session_id)
    return next(t for t in tools if t.name == "use_skill")


# ---------- 校验 ----------

def test_validate_rejects_bad_paths_and_caps():
    with pytest.raises(ValueError):
        validate_skill_files([{"path": "../escape.py", "content": "x"}])
    with pytest.raises(ValueError):
        validate_skill_files([{"path": "a.py", "content": "z" * (64 * 1024 + 1)}])
    with pytest.raises(ValueError):
        validate_skill_files([{"path": f"f{i}.py", "content": "x"} for i in range(21)])
    # 正常路径规范化
    ok = validate_skill_files([{"path": "/leading/slash.py", "content": "hi"}])
    assert ok[0]["path"] == "leading/slash.py" and ok[0]["size"] == 2


# ---------- service + 级联 ----------

async def test_create_skill_with_files_and_cascade_delete(async_session):
    svc = SkillService(async_session)
    skill = await svc.create_skill({
        "user_id": 9,
        "name": "demo",
        "content": "body",
        "files": [{"path": "a.py", "content": "print(1)"}, {"path": "n.txt", "content": "x"}],
    })
    rows = (await async_session.execute(
        select(SkillFile).where(SkillFile.skill_id == skill.id)
    )).scalars().all()
    assert {r.path for r in rows} == {"a.py", "n.txt"}

    # 删 skill → 文件级联删除（SQLite PRAGMA foreign_keys 已开）
    await svc.delete_skill(skill.id)
    left = (await async_session.execute(
        select(SkillFile).where(SkillFile.skill_id == skill.id)
    )).scalars().all()
    assert left == []


# ---------- use_skill 物化 ----------

async def test_use_skill_materializes_files(
    workspace_env, async_engine, async_session, patched_session_factory
):
    svc = SkillService(async_session)
    await svc.create_skill({
        "user_id": 5,
        "name": "kit",
        "content": "说明正文",
        "files": [{"path": "run.py", "content": "print('hi')"}, {"path": "ref.md", "content": "doc"}],
    })

    tool = _use_skill_tool(5, "sess-1")
    out = json.loads(await tool._arun(name="kit"))

    assert out["content"] == "说明正文"
    assert set(out["files"]) == {".skills/kit/run.py", ".skills/kit/ref.md"}
    assert out["runnable"] == [".skills/kit/run.py"]

    ws = Path(settings.WORKSPACE_DIR) / "5" / "sess-1" / ".skills" / "kit"
    assert (ws / "run.py").read_text(encoding="utf-8") == "print('hi')"
    assert (ws / "ref.md").read_text(encoding="utf-8") == "doc"

    # 物化不应登记 ChatFile（保持工作区面板干净）
    rows = (await async_session.execute(select(ChatFile))).scalars().all()
    assert rows == []


# ---------- python_exec script 模式 ----------

async def test_python_exec_script_mode_runs_and_registers_product(
    workspace_env, async_engine, async_session, patched_session_factory
):
    svc = SkillService(async_session)
    await svc.create_skill({
        "user_id": 6,
        "name": "writer",
        "content": "writes a file",
        "files": [{"path": "gen.py", "content": "open('out.txt','w').write('generated'); print('done')"}],
    })
    await _use_skill_tool(6, "sess-2")._arun(name="writer")

    py = PythonExecTool(user_id=6, session_id="sess-2")
    payload = json.loads(await py._arun(script=".skills/writer/gen.py"))

    assert payload["exit_code"] == 0
    assert "done" in payload["stdout"]
    # 脚本产出的 out.txt 登记为 workspace 文件
    names = {Path(f["path"]).name for f in payload["files"]}
    assert "out.txt" in names
    rows = (await async_session.execute(select(ChatFile))).scalars().all()
    assert {r.storage_type for r in rows} == {"workspace"}


async def test_script_import_os_is_blocked(
    workspace_env, async_engine, async_session, patched_session_factory
):
    svc = SkillService(async_session)
    await svc.create_skill({
        "user_id": 7,
        "name": "evil",
        "content": "tries os",
        "files": [{"path": "bad.py", "content": "import os\nprint(os.getcwd())"}],
    })
    await _use_skill_tool(7, "sess-3")._arun(name="evil")

    py = PythonExecTool(user_id=7, session_id="sess-3")
    payload = json.loads(await py._arun(script=".skills/evil/bad.py"))
    assert payload["exit_code"] != 0
    assert "安全拦截" in payload["stderr"]


async def test_python_exec_requires_code_or_script():
    tool = PythonExecTool()  # no session
    out = json.loads(await tool._arun())
    assert "error" in out
