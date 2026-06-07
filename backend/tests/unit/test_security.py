from datetime import timedelta

import pytest
from jose import ExpiredSignatureError, jwt

from app.core.config import settings
from app.core.security import create_access_token, create_jwt_token, create_refresh_token


class TestCreateJwtToken:
    def test_contains_expected_claims(self):
        token = create_jwt_token({"sub": "42"}, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "42"
        assert "exp" in payload
        assert "iat" in payload

    def test_expired_token_raises(self):
        token = create_jwt_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(ExpiredSignatureError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    def test_custom_payload_preserved(self):
        token = create_jwt_token({"role": "admin", "uid": 7}, expires_delta=timedelta(hours=1))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["role"] == "admin"
        assert payload["uid"] == 7


class TestCreateAccessToken:
    def test_claims(self):
        token = create_access_token("99", "admin")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "99"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_different_users_produce_different_tokens(self):
        t1 = create_access_token("1", "user")
        t2 = create_access_token("2", "user")
        assert t1 != t2


class TestCreateRefreshToken:
    def test_claims(self):
        token, jti = create_refresh_token("55", "user")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "55"
        assert payload["role"] == "user"
        assert payload["jti"] == jti
        assert payload["type"] == "refresh"

    def test_unique_jti_per_call(self):
        _, jti1 = create_refresh_token("1", "user")
        _, jti2 = create_refresh_token("1", "user")
        assert jti1 != jti2
