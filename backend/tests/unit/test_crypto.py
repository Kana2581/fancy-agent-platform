"""Unit tests for app.core.crypto (symmetric encryption of secret columns)."""
from app.core.crypto import decrypt_str, encrypt_str


def test_roundtrip():
    plain = "sk-1234567890abcdef"
    token = encrypt_str(plain)
    assert token != plain  # 密文不等于明文
    assert decrypt_str(token) == plain


def test_decrypt_plaintext_returns_as_is():
    # 历史明文行：非合法密文应原样返回，保证兼容读
    legacy = "sk-plaintext-key"
    assert decrypt_str(legacy) == legacy


def test_decrypt_empty_string():
    assert decrypt_str("") == ""


def test_two_encryptions_both_decrypt():
    plain = "my-secret"
    a = encrypt_str(plain)
    b = encrypt_str(plain)
    # Fernet 含随机 IV/时间戳，两次密文不同，但都能解回原文
    assert decrypt_str(a) == plain
    assert decrypt_str(b) == plain
