from typing import List, Dict, Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.user_mapper import UserMapper
from app.models.user import User
from app.utils.password_util import pwd_context


class UserService:
    def __init__(self, db: AsyncSession):
        self.db: AsyncSession = db
        self.user_mapper = UserMapper(db)


    async def register_user(self, data: dict) -> User:
        # 检查邮箱/用户名是否存在
        if await self.user_mapper.exists(email=data.get("email")):
            raise HTTPException(status_code=400, detail="Email already exists")
        if await self.user_mapper.exists(username=data.get("username")):
            raise HTTPException(status_code=400, detail="Username already exists")

        # 密码加密
        password = data.pop("password")
        hashed_password = pwd_context.hash(password)
        data["password_hash"] = hashed_password
        # 创建用户
        user = await self.user_mapper.create_from_dict(data)
        await self.db.commit()
        return user

        # ================= 登录 =================

    async def authenticate_user(self, identifier: str, password: str) -> User:
        # 查用户

        user = await self.user_mapper.get_user_by_email_or_username(identifier)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid email or password")



        # 验证密码
        if not pwd_context.verify(password, user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid email or password")
        return user

    # ================= 查询 =================

    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.user_mapper.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def get_user_by_email(self, email: str) -> User:
        stmt_filters = {"email": email}
        users = await self.user_mapper.list_by_filters(stmt_filters)
        if not users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return users[0]

    async def list_users(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[User]:
        filters = filters or {}
        return await self.user_mapper.list_by_filters(filters, offset, limit)



    # ================= 更新 =================

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> User:
        user = await self.user_mapper.update_by_id(user_id, data)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        await self.db.commit()
        return user

    # ================= 删除 =================

    async def delete_user(self, user_id: int) -> None:
        deleted = await self.user_mapper.delete_by_id(user_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    async def delete_users_bulk(self, user_ids: List[int]) -> int:
        count = await self.user_mapper.delete_by_ids(user_ids)
        if count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No users deleted")
        await self.db.commit()
        return count
