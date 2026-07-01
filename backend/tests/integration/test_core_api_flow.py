from __future__ import annotations

from langchain_core.messages import AIMessage

from app.services.scheduled_task_service import ScheduledTaskService


async def _create_llm(api_client, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "base_url": "https://api.example.test/v1",
        "api_key": "sk-test-not-real",
        **overrides,
    }
    response = await api_client.post("/api/v1/llm", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _create_agent(api_client, headers: dict[str, str], llm_id: int, **overrides) -> dict:
    payload = {
        "model_id": llm_id,
        "description": "test agent",
        "system_prompt": "You are a test agent.",
        "max_token_size": 4096,
        "human_in_the_loop": False,
        **overrides,
    }
    response = await api_client.post("/api/v1/agents/", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _create_session(api_client, headers: dict[str, str], agent_id: int, **overrides) -> dict:
    payload = {
        "agent_id": agent_id,
        "title": "Test session",
        "is_active": True,
        **overrides,
    }
    response = await api_client.post("/api/v1/sessions", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _create_scheduled_task(api_client, headers: dict[str, str], agent_id: int, **overrides) -> dict:
    payload = {
        "agent_id": agent_id,
        "name": "Daily summary",
        "instruction": "Summarize the day",
        "schedule_type": "daily",
        "schedule_time": "09:00",
        "timezone": "Asia/Shanghai",
        **overrides,
    }
    response = await api_client.post("/api/v1/scheduled-tasks", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_auth_register_login_and_protected_endpoint(api_client, create_user_and_login):
    user, headers = await create_user_and_login(username="authuser", email="auth@example.com")

    assert user["email"] == "auth@example.com"
    assert user["username"] == "authuser"
    assert "password" not in user
    assert "password_hash" not in user

    protected = await api_client.get("/protected", headers=headers)
    assert protected.status_code == 200
    assert protected.json()["user_id"] == user["id"]


async def test_auth_wrong_password_and_missing_token(api_client, create_user_and_login):
    await create_user_and_login(username="wrongpass", email="wrongpass@example.com")

    bad_login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": "wrongpass", "password": "incorrect"},
    )
    assert bad_login.status_code == 400

    no_token = await api_client.get("/api/v1/llm")
    assert no_token.status_code == 401


async def test_llm_crud_scoping_and_api_key_redaction(api_client, create_user_and_login):
    _, headers = await create_user_and_login(username="llmowner", email="llmowner@example.com")
    _, other_headers = await create_user_and_login(username="llmother", email="llmother@example.com")

    llm = await _create_llm(api_client, headers, api_key="sk-secret-value")
    assert llm["provider"] == "openai"
    assert llm["model_name"] == "gpt-4o-mini"
    assert "api_key" not in llm

    listing = await api_client.get("/api/v1/llm", headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [llm["id"]]
    assert all("api_key" not in item for item in listing.json())

    fetched = await api_client.get(f"/api/v1/llm/{llm['id']}", headers=headers)
    assert fetched.status_code == 200
    assert "api_key" not in fetched.json()

    blocked_get = await api_client.get(f"/api/v1/llm/{llm['id']}", headers=other_headers)
    assert blocked_get.status_code == 404

    blocked_update = await api_client.put(
        f"/api/v1/llm/{llm['id']}",
        json={"model_name": "blocked"},
        headers=other_headers,
    )
    assert blocked_update.status_code == 404

    updated = await api_client.put(
        f"/api/v1/llm/{llm['id']}",
        json={"model_name": "gpt-4.1-mini"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["model_name"] == "gpt-4.1-mini"
    assert "api_key" not in updated.json()

    blocked_delete = await api_client.delete(f"/api/v1/llm/{llm['id']}", headers=other_headers)
    assert blocked_delete.status_code == 404

    deleted = await api_client.delete(f"/api/v1/llm/{llm['id']}", headers=headers)
    assert deleted.status_code == 204

    missing = await api_client.get(f"/api/v1/llm/{llm['id']}", headers=headers)
    assert missing.status_code == 404


async def test_llm_test_endpoint_uses_mock_model(api_client, create_user_and_login, monkeypatch):
    _, headers = await create_user_and_login(username="llmtest", email="llmtest@example.com")

    class FakeChatModel:
        async def ainvoke(self, _input):
            return AIMessage(content="mock model ok")

    monkeypatch.setattr(
        "app.services.llm_service.init_chat_model",
        lambda **_kwargs: FakeChatModel(),
    )

    response = await api_client.post(
        "/api/v1/llm/test",
        json={
            "provider": "openai",
            "model_name": "mock-model",
            "base_url": "https://api.example.test/v1",
            "api_key": "sk-test-not-real",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "mock model ok" in body["message"]


async def test_llm_test_endpoint_handles_missing_key_and_mock_failure(
    api_client,
    create_user_and_login,
    monkeypatch,
):
    _, headers = await create_user_and_login(username="llmfail", email="llmfail@example.com")

    missing_key = await api_client.post(
        "/api/v1/llm/test",
        json={"provider": "openai", "model_name": "mock-model"},
        headers=headers,
    )
    assert missing_key.status_code == 200
    assert missing_key.json()["success"] is False
    assert "API Key" in missing_key.json()["message"]

    class FailingChatModel:
        async def ainvoke(self, _input):
            raise RuntimeError("mock model unavailable")

    monkeypatch.setattr(
        "app.services.llm_service.init_chat_model",
        lambda **_kwargs: FailingChatModel(),
    )

    failed = await api_client.post(
        "/api/v1/llm/test",
        json={
            "provider": "openai",
            "model_name": "mock-model",
            "api_key": "sk-test-not-real",
        },
        headers=headers,
    )
    assert failed.status_code == 200
    assert failed.json()["success"] is False
    assert "mock model unavailable" in failed.json()["message"]


async def test_agent_crud_full_detail_and_user_scoping(api_client, create_user_and_login):
    _, headers = await create_user_and_login(username="agentowner", email="agentowner@example.com")
    _, other_headers = await create_user_and_login(username="agentother", email="agentother@example.com")
    llm = await _create_llm(api_client, headers)
    other_llm = await _create_llm(api_client, other_headers)

    agent = await _create_agent(api_client, headers, llm["id"])
    other_agent = await _create_agent(api_client, other_headers, other_llm["id"])

    listing = await api_client.get("/api/v1/agents/", headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [agent["id"]]

    detail = await api_client.get(f"/api/v1/agents/{agent['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["llm"]["id"] == llm["id"]
    assert detail.json()["llm"]["model_name"] == llm["model_name"]

    blocked_detail = await api_client.get(f"/api/v1/agents/{other_agent['id']}", headers=headers)
    assert blocked_detail.status_code == 404

    updated = await api_client.put(
        f"/api/v1/agents/{agent['id']}",
        json={
            "model_id": llm["id"],
            "system_prompt": "Updated prompt",
            "human_in_the_loop": True,
            "max_token_size": 2048,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["system_prompt"] == "Updated prompt"
    assert updated.json()["human_in_the_loop"] is True

    blocked_update = await api_client.put(
        f"/api/v1/agents/{agent['id']}",
        json={"model_id": other_llm["id"], "system_prompt": "blocked"},
        headers=other_headers,
    )
    assert blocked_update.status_code == 404


async def test_session_crud_pagination_and_user_scoping(api_client, create_user_and_login):
    _, headers = await create_user_and_login(username="sessionowner", email="sessionowner@example.com")
    _, other_headers = await create_user_and_login(username="sessionother", email="sessionother@example.com")
    llm = await _create_llm(api_client, headers)
    agent = await _create_agent(api_client, headers, llm["id"])
    other_llm = await _create_llm(api_client, other_headers)
    other_agent = await _create_agent(api_client, other_headers, other_llm["id"])

    session = await _create_session(api_client, headers, agent["id"])
    other_session = await _create_session(api_client, other_headers, other_agent["id"])

    listing = await api_client.get("/api/v1/sessions?page=1&page_size=10", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert [item["id"] for item in listing.json()["items"]] == [session["id"]]

    fetched = await api_client.get(f"/api/v1/sessions/{session['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Test session"

    blocked_get = await api_client.get(f"/api/v1/sessions/{other_session['id']}", headers=headers)
    assert blocked_get.status_code == 404

    updated = await api_client.put(
        f"/api/v1/sessions/{session['id']}",
        json={"title": "Renamed", "is_active": False},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed"
    assert updated.json()["is_active"] is False

    blocked_update = await api_client.put(
        f"/api/v1/sessions/{session['id']}",
        json={"title": "blocked"},
        headers=other_headers,
    )
    assert blocked_update.status_code == 404

    blocked_delete = await api_client.delete(f"/api/v1/sessions/{session['id']}", headers=other_headers)
    assert blocked_delete.status_code == 404

    deleted = await api_client.delete(f"/api/v1/sessions/{session['id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"success": True}


async def test_scheduled_task_crud_executions_and_mocked_run(api_client, create_user_and_login, monkeypatch):
    _, headers = await create_user_and_login(username="taskowner", email="taskowner@example.com")
    _, other_headers = await create_user_and_login(username="taskother", email="taskother@example.com")
    llm = await _create_llm(api_client, headers)
    agent = await _create_agent(api_client, headers, llm["id"])

    task = await _create_scheduled_task(api_client, headers, agent["id"])
    assert task["next_run_at"] is not None
    assert task["is_enabled"] is True

    listing = await api_client.get("/api/v1/scheduled-tasks", headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [task["id"]]

    blocked_update = await api_client.put(
        f"/api/v1/scheduled-tasks/{task['id']}",
        json={"name": "blocked"},
        headers=other_headers,
    )
    assert blocked_update.status_code == 404

    updated = await api_client.put(
        f"/api/v1/scheduled-tasks/{task['id']}",
        json={"schedule_time": "10:30", "is_enabled": False},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["schedule_time"] == "10:30"
    assert updated.json()["is_enabled"] is False

    executions = await api_client.get(
        f"/api/v1/scheduled-tasks/{task['id']}/executions",
        headers=headers,
    )
    assert executions.status_code == 200
    assert executions.json() == {"items": [], "total": 0}

    async def fake_run_now(self, task_id: int, user_id: int) -> bool:
        assert task_id == task["id"]
        assert user_id == task["user_id"]
        return True

    monkeypatch.setattr(ScheduledTaskService, "run_now", fake_run_now)
    run_now = await api_client.post(f"/api/v1/scheduled-tasks/{task['id']}/run", headers=headers)
    assert run_now.status_code == 200
    assert run_now.json() == {"success": True}

    deleted = await api_client.delete(f"/api/v1/scheduled-tasks/{task['id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"success": True}

    missing_delete = await api_client.delete(f"/api/v1/scheduled-tasks/{task['id']}", headers=headers)
    assert missing_delete.status_code == 404


async def test_scheduled_task_run_missing_task_returns_404(api_client, create_user_and_login):
    _, headers = await create_user_and_login(username="taskmissing", email="taskmissing@example.com")

    response = await api_client.post("/api/v1/scheduled-tasks/99999/run", headers=headers)
    assert response.status_code == 404
