from pathlib import Path

from app.core.config import settings
from app.services.skill_catalog_service import scan_skill_catalog, resolve_skill_file


def _write_package(root: Path, name: str, body: str = "# Body") -> None:
    package = root / name
    package.mkdir(parents=True)
    (package / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test {name}\n---\n\n{body}\n",
        encoding="utf-8",
    )


def test_catalog_scans_system_and_user_packages(tmp_path, monkeypatch):
    system_root = tmp_path / "system"
    user_root = tmp_path / "user"
    _write_package(system_root, "system-tool")
    _write_package(user_root / "7", "user-tool")
    (user_root / "7" / "broken").mkdir(parents=True)

    monkeypatch.setattr(settings, "SYSTEM_SKILLS_DIR", str(system_root))
    monkeypatch.setattr(settings, "USER_SKILLS_DIR", str(user_root))

    entries = scan_skill_catalog(7)

    assert {(entry.scope, entry.package_path, entry.status) for entry in entries} == {
        ("system", "system-tool", "ready"),
        ("user", "user-tool", "ready"),
        ("user", "broken", "invalid"),
    }


def test_catalog_file_resolution_rejects_escape(tmp_path, monkeypatch):
    user_root = tmp_path / "user"
    _write_package(user_root / "7", "demo")
    monkeypatch.setattr(settings, "USER_SKILLS_DIR", str(user_root))

    assert resolve_skill_file("user", 7, "demo", "SKILL.md").is_file()

    try:
        resolve_skill_file("user", 7, "demo", "../outside.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal should be rejected")
