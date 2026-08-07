import json

from app.utils.langchain.builtin_tools import bash_exec
from app.utils.langchain.builtin_tools.bash_exec import BashExecTool


async def test_bash_requires_remote_sandbox(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "SANDBOX_EXEC_URL", "")
    payload = json.loads(await BashExecTool(user_id=1, session_id="session")._arun("echo hi"))
    assert "sandbox 服务未配置" in payload["error"]


async def test_bash_does_not_append_full_skill_catalog(monkeypatch):
    class FakeSandboxClient:
        async def execute(self, **kwargs):
            return {
                "stdout": "ok",
                "stderr": "",
                "exit_code": 0,
                "changed_files": [],
                "skill_changed_files": [{"path": "demo/SKILL.md", "size": 10}],
            }

    monkeypatch.setattr(bash_exec, "sandbox_client", lambda: FakeSandboxClient())
    monkeypatch.setattr(bash_exec, "skill_root_mounts", lambda user_id: [])

    payload = json.loads(await BashExecTool(user_id=1, session_id="session")._arun("echo hi"))

    assert payload["stdout"] == "ok"
    assert payload["skill_changed_files"] == [{"path": "demo/SKILL.md", "size": 10}]
    assert "skills" not in payload
    assert "skills_error" not in payload
