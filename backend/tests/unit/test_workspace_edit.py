import json

from app.utils.langchain.builtin_tools import workspace_tool


async def test_ws_edit_previews_in_sandbox_without_reading_file_content(monkeypatch):
    calls = []

    class FakeSandboxClient:
        async def workspace(self, operation, rel_dir, **payload):
            calls.append((operation, rel_dir, payload))
            assert operation == "edit"
            if payload.get("dry_run"):
                return {"path": "large.txt", "replaced": 1, "old_size": 40_006, "size": 40_007}
            return {"path": "large.txt", "replaced": 1, "size": 40_007}

    async def check_quota(user_id, session_id, incoming_bytes, final_file_size):
        assert (user_id, session_id) == (7, "session-a")
        assert incoming_bytes == 1
        assert final_file_size == 40_007

    async def register(*_args, **_kwargs):
        return 123

    monkeypatch.setattr(workspace_tool, "sandbox_client", lambda: FakeSandboxClient())
    monkeypatch.setattr(workspace_tool, "check_quota", check_quota)
    monkeypatch.setattr(workspace_tool, "_register_workspace_file", register)
    edit_tool = next(tool for tool in workspace_tool.build_workspace_tools(7, "session-a") if tool.name == "ws_edit")

    result = json.loads(await edit_tool._arun("large.txt", "target", "updated"))

    assert result == {"path": "large.txt", "replaced": 1, "file_id": 123}
    assert [operation for operation, _, _ in calls] == ["edit", "edit"]
    assert calls[0][2]["dry_run"] is True
    assert "dry_run" not in calls[1][2]
