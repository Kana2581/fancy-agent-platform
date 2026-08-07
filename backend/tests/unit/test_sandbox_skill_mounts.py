import importlib.util
import sys
from pathlib import Path

import pytest

from app.utils import sandbox_runner


SANDBOX_SERVER_PATH = Path(__file__).parents[3] / "sandbox" / "server.py"
sys.modules.setdefault("sandbox_runner", sandbox_runner)
spec = importlib.util.spec_from_file_location("sandbox_server", SANDBOX_SERVER_PATH)
assert spec and spec.loader
sandbox_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sandbox_server)


def test_user_skill_mount_resolves_under_user_directory(tmp_path, monkeypatch):
    user_root = (tmp_path / "user").resolve()
    expected = user_root / "7" / "hello-trilingual"
    wrong_legacy_path = user_root / "hello-trilingual"
    expected.mkdir(parents=True)
    wrong_legacy_path.mkdir(parents=True)
    monkeypatch.setattr(sandbox_server, "USER_SKILLS_ROOT", user_root)

    mounts = sandbox_server._resolve_skill_mounts([
        sandbox_server.SkillMount(
            skill_id=42,
            source_type="user",
            user_id=7,
            package_path="hello-trilingual",
            read_only=False,
        )
    ])

    assert mounts == [(expected.resolve(), Path("/skills/user/hello-trilingual"), False)]


def test_user_skill_mount_requires_user_id(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox_server, "USER_SKILLS_ROOT", (tmp_path / "user").resolve())

    with pytest.raises(ValueError, match="user_id"):
        sandbox_server._resolve_skill_mounts([
            sandbox_server.SkillMount(
                skill_id=42,
                source_type="user",
                package_path="42",
            )
        ])


def test_skill_root_mounts_are_scoped_and_user_root_is_writable(tmp_path, monkeypatch):
    system_root = (tmp_path / "system").resolve()
    user_root = (tmp_path / "user").resolve()
    system_root.mkdir()
    monkeypatch.setattr(sandbox_server, "SYSTEM_SKILLS_ROOT", system_root)
    monkeypatch.setattr(sandbox_server, "USER_SKILLS_ROOT", user_root)

    mounts = sandbox_server._resolve_skill_roots([
        sandbox_server.SkillRootMount(scope="system"),
        sandbox_server.SkillRootMount(scope="user", user_id=7),
    ])

    assert mounts == [
        (system_root, Path("/skills/system"), True, "system"),
        ((user_root / "7").resolve(), Path("/skills/user"), False, "user"),
    ]


@pytest.mark.parametrize(
    ("cwd", "expected"),
    [
        (None, "/workspace"),
        (".", "/workspace"),
        ("/", "/"),
        ("/workspace", "/workspace"),
        ("/skills/user/hello-trilingual", "/skills/user/hello-trilingual"),
        ("/skills/system/skill-creator", "/skills/system/skill-creator"),
    ],
)
def test_bash_cwd_allows_sandbox_paths(tmp_path, cwd, expected):
    assert sandbox_server._resolve_cwd(tmp_path, cwd) == expected


@pytest.mark.parametrize("cwd", ["/etc", "/workspaces", "../outside", "/workspace/../outside"])
def test_bash_cwd_rejects_escape_paths(tmp_path, cwd):
    with pytest.raises(ValueError):
        sandbox_server._resolve_cwd(tmp_path, cwd)
