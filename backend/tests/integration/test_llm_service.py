import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.llm_schema import LLMOut, LLMUpdate
from app.services.llm_service import LLMService


def _make_data(user_id: int = 1, **overrides) -> dict:
    return {
        "user_id": user_id,
        "provider": "openai",
        "model_name": "gpt-4o",
        "base_url": "https://api.example.com/v1",
        "api_key": "sk-placeholder-not-real",
        **overrides,
    }


class TestLLMServiceCrud:
    async def test_create_and_get(self, async_session: AsyncSession):
        service = LLMService(async_session)
        llm = await service.create_llm(_make_data())
        fetched = await service.get_llm(llm.id)
        assert fetched is not None
        assert fetched.provider == "openai"
        assert fetched.model_name == "gpt-4o"

    async def test_get_nonexistent_returns_none(self, async_session: AsyncSession):
        assert await LLMService(async_session).get_llm(99999) is None

    async def test_list_scoped_by_user(self, async_session: AsyncSession):
        service = LLMService(async_session)
        await service.create_llm(_make_data(user_id=10))
        await service.create_llm(_make_data(user_id=10, model_name="gpt-3.5-turbo"))
        await service.create_llm(_make_data(user_id=20))

        results = await service.list_llms_by_user(10)
        assert len(results) == 2
        assert all(r.user_id == 10 for r in results)

    async def test_update_model_name(self, async_session: AsyncSession):
        service = LLMService(async_session)
        llm = await service.create_llm(_make_data())
        updated = await service.update_llm(llm.id, LLMUpdate(model_name="gpt-4-turbo"))
        assert updated is not None
        assert updated.model_name == "gpt-4-turbo"

    async def test_update_preserves_unset_fields(self, async_session: AsyncSession):
        service = LLMService(async_session)
        llm = await service.create_llm(_make_data(provider="anthropic"))
        await service.update_llm(llm.id, LLMUpdate(model_name="claude-3-5-sonnet"))
        fetched = await service.get_llm(llm.id)
        assert fetched.provider == "anthropic"

    async def test_delete(self, async_session: AsyncSession):
        service = LLMService(async_session)
        llm = await service.create_llm(_make_data())
        assert await service.delete_llm(llm.id) is True
        assert await service.get_llm(llm.id) is None

    async def test_delete_nonexistent_returns_false(self, async_session: AsyncSession):
        assert await LLMService(async_session).delete_llm(99999) is False


class TestLLMOutSchema:
    async def test_api_key_not_exposed(self, async_session: AsyncSession):
        """LLMOut deliberately omits api_key to avoid leaking credentials."""
        service = LLMService(async_session)
        llm = await service.create_llm(_make_data(api_key="sk-super-secret"))
        out = LLMOut.model_validate(llm)
        assert not hasattr(out, "api_key")
        # Serialised dict also must not contain the key
        assert "api_key" not in out.model_dump()

    async def test_base_url_exposed(self, async_session: AsyncSession):
        service = LLMService(async_session)
        llm = await service.create_llm(_make_data(base_url="https://custom.api/v1"))
        out = LLMOut.model_validate(llm)
        assert out.base_url == "https://custom.api/v1"


class TestApiKeyEncryptionAtRest:
    async def test_stored_value_is_ciphertext(self, async_session: AsyncSession):
        """api_key 落库后是密文，ORM 读回是明文。"""
        secret = "sk-super-secret-value"
        service = LLMService(async_session)
        llm = await service.create_llm(_make_data(api_key=secret))
        llm_id = llm.id

        # 原始 SQL 绕过 TypeDecorator，拿到库里真实存储值 → 应为密文
        raw = (await async_session.execute(
            text("SELECT api_key FROM llms WHERE id = :id"), {"id": llm_id}
        )).scalar_one()
        assert raw != secret
        assert secret not in raw

        # 清空 identity map，强制从库重新加载 → 透明解密为明文
        async_session.expunge_all()
        fetched = await service.get_llm(llm_id)
        assert fetched.api_key == secret

    async def test_legacy_plaintext_row_reads_back(self, async_session: AsyncSession):
        """历史明文行（绕过加密直接写入）应能正常读出。"""
        service = LLMService(async_session)
        llm = await service.create_llm(_make_data())
        llm_id = llm.id
        legacy_plain = "sk-legacy-plaintext"
        await async_session.execute(
            text("UPDATE llms SET api_key = :v WHERE id = :id"),
            {"v": legacy_plain, "id": llm_id},
        )
        await async_session.commit()
        async_session.expunge_all()

        fetched = await service.get_llm(llm_id)
        assert fetched.api_key == legacy_plain


@pytest.mark.skipif(
    not os.getenv("TEST_LLM_API_KEY"),
    reason="Set TEST_LLM_API_KEY + TEST_LLM_BASE_URL to run live connectivity tests",
)
class TestLLMServiceConnect:
    """Live connectivity test — skipped unless env vars are provided.

    Run with:
        TEST_LLM_API_KEY=sk-... TEST_LLM_BASE_URL=https://... pytest -k test_connect
    """

    async def test_connect_returns_success(self, async_session: AsyncSession):
        from app.schemas.llm_schema import LLMTestRequest

        service = LLMService(async_session)
        req = LLMTestRequest(
            provider=os.getenv("TEST_LLM_PROVIDER", "openai"),
            model_name=os.getenv("TEST_LLM_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("TEST_LLM_BASE_URL"),
            api_key=os.getenv("TEST_LLM_API_KEY"),
        )
        ok, msg = await service.test_llm(req, user_id=1)
        assert ok, f"Connection failed: {msg}"
