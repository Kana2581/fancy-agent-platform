import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.mappers.base_mapper import BaseMapper
from app.models.timestamp_model import TimestampMixin


# Minimal model used only in this test module.
# Registered with Base.metadata at import time, so create_all in conftest includes it.
class Item(Base, TimestampMixin):
    __tablename__ = "test_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)


class ItemMapper(BaseMapper[Item]):
    model = Item


class TestBaseMapperCrud:
    async def test_create_and_get_by_id(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        item = await mapper.create_from_dict({"name": "apple", "value": 10})
        await async_session.commit()

        fetched = await mapper.get_by_id(item.id)
        assert fetched is not None
        assert fetched.name == "apple"
        assert fetched.value == 10

    async def test_get_nonexistent_returns_none(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        assert await mapper.get_by_id(99999) is None

    async def test_list_by_filters_single_field(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        await mapper.create_from_dict({"name": "banana", "value": 5})
        await mapper.create_from_dict({"name": "cherry", "value": 5})
        await mapper.create_from_dict({"name": "date", "value": 99})
        await async_session.commit()

        results = await mapper.list_by_filters({"value": 5})
        assert len(results) == 2
        assert {r.name for r in results} == {"banana", "cherry"}

    async def test_list_by_filters_empty_matches_all(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        await mapper.create_from_dict({"name": "a", "value": 1})
        await mapper.create_from_dict({"name": "b", "value": 2})
        await async_session.commit()

        results = await mapper.list_by_filters({})
        assert len(results) >= 2

    async def test_update_by_id(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        item = await mapper.create_from_dict({"name": "old", "value": 1})
        await async_session.commit()

        updated = await mapper.update_by_id(item.id, {"name": "new", "value": 99})
        await async_session.commit()

        assert updated is not None
        assert updated.name == "new"
        assert updated.value == 99

    async def test_update_nonexistent_returns_none(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        assert await mapper.update_by_id(99999, {"name": "ghost"}) is None

    async def test_delete_by_id(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        item = await mapper.create_from_dict({"name": "to_delete", "value": 0})
        await async_session.commit()

        assert await mapper.delete_by_id(item.id) is True
        await async_session.commit()
        assert await mapper.get_by_id(item.id) is None

    async def test_delete_nonexistent_returns_false(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        assert await mapper.delete_by_id(99999) is False

    async def test_bulk_create_from_dicts(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        items = await mapper.bulk_create_from_dicts([
            {"name": "x", "value": 1},
            {"name": "y", "value": 2},
            {"name": "z", "value": 3},
        ])
        await async_session.commit()
        assert len(items) == 3
        assert {i.name for i in items} == {"x", "y", "z"}

    async def test_delete_by_ids(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        items = await mapper.bulk_create_from_dicts([
            {"name": "del_a", "value": 1},
            {"name": "del_b", "value": 2},
        ])
        await async_session.commit()

        count = await mapper.delete_by_ids([i.id for i in items])
        await async_session.commit()
        assert count == 2

    async def test_delete_by_ids_empty_list(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        count = await mapper.delete_by_ids([])
        assert count == 0

    async def test_exists_true(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        await mapper.create_from_dict({"name": "unique_xyz", "value": 7})
        await async_session.commit()
        assert await mapper.exists(name="unique_xyz") is True

    async def test_exists_false(self, async_session: AsyncSession):
        mapper = ItemMapper(async_session)
        assert await mapper.exists(name="does_not_exist_ever") is False
