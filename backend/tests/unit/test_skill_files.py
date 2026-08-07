"""Skill package creation and validation tests。

覆盖：
- SkillService.create_skill(files=...) 落 skill_files 行；删 skill 级联删文件
- 文件校验：越界 path / 超 caps 抛 ValueError
- default create_skill tool：创建标准用户 Skill package
"""
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.skill import Skill
from app.models.skill_file import SkillFile
from app.schemas.skill_schema import SkillUpdate
from app.services.skill_service import SkillService, validate_skill_files
from app.utils.langchain.builtin_tools.python_exec import PythonExecTool


@pytest.fixture
def workspace_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SANDBOX_EXEC_URL", "")
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path / "workspaces"))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "USER_SKILLS_DIR", str(tmp_path / "skills"))
    monkeypatch.setattr(settings, "OSS_URL", "http://test-oss")
    return tmp_path


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


async def test_legacy_session_scope_is_rejected(async_session):
    with pytest.raises(ValueError, match="仅支持创建 user Skill"):
        await SkillService(async_session).create_skill({
            "user_id": 9,
            "name": "session-demo",
            "content": "body",
            "scope": "session",
            "session_id": "session-1",
        })


async def test_purge_legacy_session_skill_removes_package(workspace_env, async_session):
    legacy = Skill(
        user_id=9,
        name="legacy-session",
        content="body",
        scope="session",
        source_type="session",
        package_path="17",
    )
    async_session.add(legacy)
    await async_session.flush()

    package = Path(settings.USER_SKILLS_DIR) / "9" / "17"
    package.mkdir(parents=True)
    (package / "SKILL.md").write_text("legacy", encoding="utf-8")

    assert await SkillService(async_session).purge_legacy_session_skills() == 1
    assert not package.exists()
    assert await SkillService(async_session).get_skill(legacy.id) is None


async def test_user_skill_directory_uses_name_and_renames(workspace_env, async_session):
    service = SkillService(async_session)
    skill = await service.create_skill({
        "user_id": 9,
        "name": " hello-trilingual ",
        "content": "body",
    })
    original = Path(settings.USER_SKILLS_DIR) / "9" / "hello-trilingual"
    assert skill.name == "hello-trilingual"
    assert skill.package_path == "hello-trilingual"
    assert original.is_dir()

    updated = await service.update_skill(skill.id, SkillUpdate(name="bonjour-trilingual"))
    renamed = Path(settings.USER_SKILLS_DIR) / "9" / "bonjour-trilingual"
    assert updated is not None
    assert updated.package_path == "bonjour-trilingual"
    assert renamed.is_dir()
    assert not original.exists()


async def test_python_exec_requires_code_or_script():
    tool = PythonExecTool()  # no session
    out = json.loads(await tool._arun())
    assert "error" in out
