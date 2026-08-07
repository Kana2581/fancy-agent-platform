from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.api.skill_router import _serialize_skill
from app.core.config import settings
from app.mappers.skill_mapper import SkillMapper
from app.models.skill import Skill
from app.services.skill_package_service import package_dir, scan_package, write_package
from app.services.skill_service import SkillService


def test_package_round_trip_and_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "USER_SKILLS_DIR", str(tmp_path / "user"))
    metadata = write_package(
        "user", 7, "42", name="demo", description="A demo Skill", content="# Body",
        files=[{"path": "scripts/run.py", "content": "print('ok')"}],
    )
    assert metadata.name == "demo"
    assert {item["path"] for item in metadata.files} == {"SKILL.md", "scripts/run.py"}
    assert "name: demo" in (tmp_path / "user" / "7" / "42" / "SKILL.md").read_text(encoding="utf-8")
    assert scan_package("user", 7, "42").content_hash == metadata.content_hash


def test_package_path_and_frontmatter_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "USER_SKILLS_DIR", str(tmp_path / "user"))
    with pytest.raises(ValueError, match="path"):
        package_dir("user", 7, "../outside")
    root = tmp_path / "user" / "7" / "bad"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text("# missing frontmatter\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        scan_package("user", 7, "bad")


def test_skill_serialization_skips_binary_assets(tmp_path, monkeypatch):
    root = tmp_path / "system"
    package = root / "demo"
    (package / "assets").mkdir(parents=True)
    (package / "SKILL.md").write_text(
        "---\nname: demo\ndescription: A demo skill\n---\n\n# Body\n",
        encoding="utf-8",
    )
    (package / "notes.txt").write_text("plain text", encoding="utf-8")
    (package / "assets" / "demo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(settings, "SYSTEM_SKILLS_DIR", str(root))

    now = datetime.now(timezone.utc)
    skill = SimpleNamespace(
        id=1,
        user_id=0,
        name="demo",
        content="legacy",
        description="legacy",
        category=None,
        scope="system",
        session_id="",
        source_type="system",
        package_path="demo",
        package_status="ready",
        content_hash=None,
        last_scanned_at=None,
        files=[],
        created_at=now,
        updated_at=now,
    )

    out = _serialize_skill(skill)

    assert out.package_status == "ready"
    assert {item.path for item in out.files} == {"SKILL.md", "notes.txt"}


@pytest.mark.parametrize(
    "name",
    ["skill-creator", "report_writer", "code_review_checklist", "interview_summary", "csv_profile"],
)
def test_repository_system_skill_packages_are_valid(name, monkeypatch):
    root = Path(__file__).resolve().parents[3] / "skills"
    monkeypatch.setattr(settings, "SYSTEM_SKILLS_DIR", str(root))
    metadata = scan_package("system", None, name)

    assert metadata.name == name
    assert any(item["path"] == "SKILL.md" for item in metadata.files)


async def test_system_package_scan_registers_package_metadata(tmp_path, monkeypatch, async_session):
    root = tmp_path / "system"
    package = root / "skill-creator"
    package.mkdir(parents=True)
    (package / "SKILL.md").write_text(
        "---\nname: skill-creator\ndescription: Create skills\n---\n\n# Body\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "SYSTEM_SKILLS_DIR", str(root))

    assert await SkillService(async_session).scan_system_packages() == 1
    skill = await SkillMapper(async_session).get_system_by_name("skill-creator")
    assert skill is not None
    assert skill.source_type == "system"
    assert skill.package_path == "skill-creator"
    assert skill.package_status == "ready"


async def test_system_package_scan_invalidates_missing_package(async_session, tmp_path, monkeypatch):
    root = tmp_path / "system"
    root.mkdir()
    stale = Skill(
        user_id=0,
        name="removed",
        content="# Removed",
        scope="system",
        source_type="system",
        package_path="removed",
        package_status="ready",
    )
    async_session.add(stale)
    await async_session.flush()
    monkeypatch.setattr(settings, "SYSTEM_SKILLS_DIR", str(root))

    assert await SkillService(async_session).scan_system_packages() == 0

    current = await SkillMapper(async_session).get_by_id(stale.id)
    assert current.package_status == "invalid"
