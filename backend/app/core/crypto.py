"""对称加密工具：用于敏感字段（如 API Key）落库加密 / 读取解密。

设计要点：
- 基于 ``cryptography.fernet.Fernet``（AES-128-CBC + HMAC），已在依赖中，无需新增。
- 密钥来源：优先 ``settings.APP_ENCRYPTION_KEY``，为空则回退到 ``settings.SECRET_KEY``，
  统一经 SHA256 归一为合法的 32 字节 urlsafe-base64 Fernet key，允许用户填任意字符串。
- ``decrypt_str`` 对解密失败的输入**原样返回**，从而兼容历史明文行与意外明文。
- ``EncryptedString`` 是一个 SQLAlchemy ``TypeDecorator``：写入自动加密、读取自动解密，
  调用方（service / mapper / schema / adapter）无需任何改动。

该模块只依赖 ``app.core.config``，不导入任何 model，避免循环导入。
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.config import settings


def _derive_fernet_key(material: str) -> bytes:
    """把任意字符串归一为合法的 32 字节 urlsafe-base64 Fernet 密钥。"""
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    material = settings.APP_ENCRYPTION_KEY or settings.SECRET_KEY
    return Fernet(_derive_fernet_key(material))


def encrypt_str(value: str) -> str:
    """加密明文字符串，返回 urlsafe-base64 密文 token。"""
    token = _get_fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_str(token: str) -> str:
    """解密密文 token。

    若 ``token`` 并非本密钥产出的合法密文（例如历史明文行），则原样返回，
    保证旧数据可平滑读取。
    """
    try:
        plaintext = _get_fernet().decrypt(token.encode("utf-8"))
        return plaintext.decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        # 非合法密文（历史明文 / 损坏数据）——按明文回退，避免读取报错。
        return token


class EncryptedString(TypeDecorator):
    """透明加密的字符串列类型。

    底层用 ``TEXT`` 存储（密文比明文长，统一 TEXT 避免 VARCHAR 溢出）。
    写入时加密、读取时解密；``None`` / 空串透传。
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or value == "":
            return value
        return encrypt_str(value)

    def process_result_value(self, value, dialect):
        if value is None or value == "":
            return value
        return decrypt_str(value)
