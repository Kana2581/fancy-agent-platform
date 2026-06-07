import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import LLM
from app.services.agent_service import AgentService


class TestAgentService:
    async def _seed_llm(self, session: AsyncSession) -> LLM:
        llm = LLM(user_id=1, provider="openai", model_name="gpt-4o")
        session.add(llm)
        await session.flush()
        return llm

    async def test_create_and_get(self, async_session: AsyncSession):
        llm = await self._seed_llm(async_session)
        service = AgentService(async_session)

        agent = await service.create_agent({
            "user_id": 1,
            "model_id": llm.id,
            "system_prompt": "You are helpful.",
            "human_in_the_loop": False,
        })

        fetched = await service.get_agent(agent.id)
        assert fetched is not None
        assert fetched.system_prompt == "You are helpful."
        assert fetched.model_id == llm.id

    async def test_get_nonexistent_returns_none(self, async_session: AsyncSession):
        service = AgentService(async_session)
        assert await service.get_agent(99999) is None

    async def test_list_agents_scoped_by_user(self, async_session: AsyncSession):
        llm = await self._seed_llm(async_session)
        service = AgentService(async_session)

        await service.create_agent({"user_id": 1, "model_id": llm.id, "human_in_the_loop": False})
        await service.create_agent({"user_id": 1, "model_id": llm.id, "human_in_the_loop": False})
        await service.create_agent({"user_id": 2, "model_id": llm.id, "human_in_the_loop": False})

        agents = await service.list_agents({"user_id": 1})
        assert len(agents) == 2
        assert all(a.user_id == 1 for a in agents)

    async def test_update_agent(self, async_session: AsyncSession):
        llm = await self._seed_llm(async_session)
        service = AgentService(async_session)

        agent = await service.create_agent({
            "user_id": 1,
            "model_id": llm.id,
            "system_prompt": "old prompt",
            "human_in_the_loop": False,
        })

        updated = await service.update_agent(agent.id, {"system_prompt": "new prompt"})
        assert updated is not None
        assert updated.system_prompt == "new prompt"

    async def test_update_nonexistent_returns_none(self, async_session: AsyncSession):
        service = AgentService(async_session)
        result = await service.update_agent(99999, {"system_prompt": "ghost"})
        assert result is None

    async def test_delete_agent(self, async_session: AsyncSession):
        llm = await self._seed_llm(async_session)
        service = AgentService(async_session)

        agent = await service.create_agent({
            "user_id": 1,
            "model_id": llm.id,
            "human_in_the_loop": False,
        })

        assert await service.delete_agent(agent.id) is True
        assert await service.get_agent(agent.id) is None

    async def test_delete_nonexistent_returns_false(self, async_session: AsyncSession):
        service = AgentService(async_session)
        assert await service.delete_agent(99999) is False

    async def test_agent_exists(self, async_session: AsyncSession):
        llm = await self._seed_llm(async_session)
        service = AgentService(async_session)

        await service.create_agent({
            "user_id": 88,
            "model_id": llm.id,
            "human_in_the_loop": False,
        })

        assert await service.agent_exists(user_id=88) is True
        assert await service.agent_exists(user_id=999) is False

    async def test_human_in_the_loop_default(self, async_session: AsyncSession):
        llm = await self._seed_llm(async_session)
        service = AgentService(async_session)

        agent = await service.create_agent({
            "user_id": 1,
            "model_id": llm.id,
            "human_in_the_loop": False,
        })
        assert agent.human_in_the_loop is False
