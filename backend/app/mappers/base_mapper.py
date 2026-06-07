# app/mapper/base_mapper.py
from typing import Type, TypeVar, Generic, List, Optional, Dict, Any, Iterable

from sqlalchemy import select, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")  # SQLAlchemy Model


class BaseMapper(Generic[T]):
    """
    Mapper 基类（Async 版）
    """

    model: Type[T] = None     # 子类必须指定
    pk_name: str = "id"       # 默认主键名，可覆盖

    def __init__(self, db: AsyncSession):
        if self.model is None:
            raise ValueError("BaseMapper 子类必须指定 model")
        self.db = db

    # ================= 查询 =================

    async def get_by_id(self, id_: Any) -> Optional[T]:
        return await self.db.get(self.model, id_)

    async def list_all(self) -> List[T]:
        result = await self.db.execute(select(self.model))
        return result.scalars().all()

    async def list_by_filters(
            self,
            filters: Dict[str, Any],
            offset: int = 0,
            limit: int = 100,
    ) -> List[T]:
        stmt = select(self.model)

        # 过滤条件
        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)

        # 自动时间排序（如果存在时间字段）
        time_fields = ["updated_at", "update_time","created_at", "create_time"]

        for field in time_fields:
            if hasattr(self.model, field):
                stmt = stmt.order_by(desc(getattr(self.model, field)))
                break  # 只用第一个匹配到的时间字段

        result = await self.db.execute(stmt.offset(offset).limit(limit))
        return result.scalars().all()

    async def exists(self, **kwargs) -> bool:
        stmt = select(self.model)
        for k, v in kwargs.items():
            if hasattr(self.model, k):
                stmt = stmt.where(getattr(self.model, k) == v)

        result = await self.db.execute(stmt)
        return result.first() is not None

    # ================= 新增 =================

    async def create_from_dict(self, data: Dict[str, Any]) -> T:
        obj = self.model(**data)
        self.db.add(obj)
        await self.db.flush()
        return obj

    # （低级接口）
    async def _create_entity(self, obj: T) -> T:
        self.db.add(obj)
        await self.db.flush()
        return obj

    # ================= 更新 =================

    async def update_by_id(self, id_: Any, data: Dict[str, Any]) -> Optional[T]:
        pk = getattr(self.model, self.pk_name)

        stmt = (
            update(self.model)
            .where(pk == id_)
            .values(**data)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            return None

        return await self.get_by_id(id_)

    # （低级接口）
    async def _update_entity(self, obj: T, data: Dict[str, Any]) -> T:
        for k, v in data.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        await self.db.flush()
        return obj

    # ================= 删除 =================

    async def delete_by_id(self, id_: Any) -> bool:
        pk = getattr(self.model, self.pk_name)
        result = await self.db.execute(
            delete(self.model).where(pk == id_)
        )
        return result.rowcount > 0

    async def delete_by_ids(self, ids: List[Any]) -> int:
        """
        按主键列表批量删除
        返回删除行数
        """
        if not ids:
            return 0

        pk = getattr(self.model, self.pk_name)
        result = await self.db.execute(
            delete(self.model).where(pk.in_(ids))
        )
        return result.rowcount

    # ================= 批量操作 =================

    async def bulk_create_from_dicts(
        self,
        data_list: List[Dict[str, Any]],
        flush: bool = True,
    ) -> List[T]:
        objs = [self.model(**data) for data in data_list]
        self.db.add_all(objs)
        if flush:
            await self.db.flush()
        return objs

    async def _bulk_create_entities(
        self,
        objs: Iterable[T],
        flush: bool = True,
    ) -> List[T]:
        objs = list(objs)
        self.db.add_all(objs)
        if flush:
            await self.db.flush()
        return objs

    async def bulk_insert_mappings(self, data_list: List[Dict[str, Any]]):
        """
        超高性能批量插入（不会返回 ORM 对象）
        """
        await self.db.run_sync(
            lambda sync_db: sync_db.bulk_insert_mappings(
                self.model, data_list
            )
        )
