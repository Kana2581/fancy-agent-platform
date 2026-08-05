import json

from app.utils.langchain.builtin_tools.bash_exec import BashExecTool


async def test_bash_requires_remote_sandbox(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "SANDBOX_EXEC_URL", "")
    payload = json.loads(await BashExecTool(user_id=1, session_id="session")._arun("echo hi"))
    assert "sandbox 服务未配置" in payload["error"]
