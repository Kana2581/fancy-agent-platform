import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService


class TestUserServiceRegister:
    async def test_creates_user_with_correct_fields(self, async_session: AsyncSession):
        service = UserService(async_session)
        user = await service.register_user(
            {"email": "alice@example.com", "username": "alice", "password": "secret123"}
        )
        assert user.id is not None
        assert user.email == "alice@example.com"
        assert user.username == "alice"

    async def test_password_is_hashed(self, async_session: AsyncSession):
        service = UserService(async_session)
        user = await service.register_user(
            {"email": "bob@example.com", "username": "bob", "password": "plaintext"}
        )
        assert user.password_hash != "plaintext"
        assert len(user.password_hash) > 20

    async def test_duplicate_email_raises_400(self, async_session: AsyncSession):
        service = UserService(async_session)
        await service.register_user(
            {"email": "dup@example.com", "username": "user1", "password": "pass"}
        )
        with pytest.raises(HTTPException) as exc:
            await service.register_user(
                {"email": "dup@example.com", "username": "user2", "password": "pass"}
            )
        assert exc.value.status_code == 400
        assert "Email" in exc.value.detail

    async def test_duplicate_username_raises_400(self, async_session: AsyncSession):
        service = UserService(async_session)
        await service.register_user(
            {"email": "x@example.com", "username": "sameuser", "password": "pass"}
        )
        with pytest.raises(HTTPException) as exc:
            await service.register_user(
                {"email": "y@example.com", "username": "sameuser", "password": "pass"}
            )
        assert exc.value.status_code == 400
        assert "Username" in exc.value.detail


class TestUserServiceAuthenticate:
    async def _seed(self, session: AsyncSession, email: str, username: str, password: str):
        return await UserService(session).register_user(
            {"email": email, "username": username, "password": password}
        )

    async def test_correct_password_returns_user(self, async_session: AsyncSession):
        await self._seed(async_session, "charlie@example.com", "charlie", "rightpass")
        user = await UserService(async_session).authenticate_user(
            "charlie@example.com", "rightpass"
        )
        assert user.email == "charlie@example.com"

    async def test_login_by_username_works(self, async_session: AsyncSession):
        await self._seed(async_session, "dave@example.com", "davey", "pass123")
        user = await UserService(async_session).authenticate_user("davey", "pass123")
        assert user.username == "davey"

    async def test_wrong_password_raises_400(self, async_session: AsyncSession):
        await self._seed(async_session, "eve@example.com", "eve", "correct")
        with pytest.raises(HTTPException) as exc:
            await UserService(async_session).authenticate_user("eve@example.com", "wrong")
        assert exc.value.status_code == 400

    async def test_unknown_user_raises_400(self, async_session: AsyncSession):
        with pytest.raises(HTTPException) as exc:
            await UserService(async_session).authenticate_user("nobody@example.com", "pass")
        assert exc.value.status_code == 400
