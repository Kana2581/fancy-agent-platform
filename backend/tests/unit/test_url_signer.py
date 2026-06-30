"""Unit tests for app.services.storage.url_signer (public vs presigned URL modes)."""

from urllib.parse import urlparse, parse_qs

import pytest

from app.core.config import settings
from app.services.storage import url_signer
from app.services.storage.url_signer import (
    build_storage_url,
    extract_object_key,
    resign_url,
    rewrite_image_urls_in_text,
)
from app.schemas.chat_schema import ChatResponse

KEY = "generated/2025/01/01/abc123.png"


@pytest.fixture(autouse=True)
def _reset_signer_cache():
    # The botocore signing client is lru_cached and depends on settings; reset it
    # so each test sees a client built from its own monkeypatched config.
    url_signer._signer_client.cache_clear()
    yield
    url_signer._signer_client.cache_clear()


def _set_public(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3", raising=False)
    monkeypatch.setattr(settings, "S3_URL_MODE", "public", raising=False)
    monkeypatch.setattr(settings, "OSS_URL", "https://mybucket.oss-cn-hangzhou.aliyuncs.com", raising=False)


def _set_presigned(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3", raising=False)
    monkeypatch.setattr(settings, "S3_URL_MODE", "presigned", raising=False)
    monkeypatch.setattr(settings, "OSS_URL", "https://mybucket.oss-cn-hangzhou.aliyuncs.com", raising=False)
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "https://oss-cn-hangzhou.aliyuncs.com", raising=False)
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "AKIDEXAMPLE", raising=False)
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "secretkeyexample", raising=False)
    monkeypatch.setattr(settings, "S3_BUCKET", "mybucket", raising=False)
    monkeypatch.setattr(settings, "S3_REGION", "cn-hangzhou", raising=False)
    monkeypatch.setattr(settings, "S3_PRESIGN_EXPIRE", 3600, raising=False)


# --------------------------------------------------------------------------- #
# build_storage_url
# --------------------------------------------------------------------------- #

def test_public_mode_returns_plain_url(monkeypatch):
    _set_public(monkeypatch)
    assert build_storage_url(KEY) == f"https://mybucket.oss-cn-hangzhou.aliyuncs.com/{KEY}"


def test_local_backend_returns_plain_url(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local", raising=False)
    monkeypatch.setattr(settings, "S3_URL_MODE", "presigned", raising=False)  # ignored for local
    monkeypatch.setattr(settings, "OSS_URL", "http://localhost:8000", raising=False)
    assert build_storage_url(KEY) == f"http://localhost:8000/{KEY}"


def test_presigned_mode_signs_url(monkeypatch):
    _set_presigned(monkeypatch)
    url = build_storage_url(KEY)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # path is the object_key; query carries an expiring s3v4 signature
    assert parsed.path.lstrip("/") == KEY
    assert "X-Amz-Signature" in qs
    assert "X-Amz-Expires" in qs


# --------------------------------------------------------------------------- #
# extract_object_key
# --------------------------------------------------------------------------- #

def test_extract_from_plain_internal_url(monkeypatch):
    _set_public(monkeypatch)
    url = f"https://mybucket.oss-cn-hangzhou.aliyuncs.com/{KEY}"
    assert extract_object_key(url) == KEY


def test_extract_drops_stale_signature(monkeypatch):
    _set_presigned(monkeypatch)
    signed = build_storage_url(KEY)
    # even with a (possibly expired) signature query, key is recovered from the path
    assert extract_object_key(signed) == KEY


def test_extract_external_url_returns_none(monkeypatch):
    _set_presigned(monkeypatch)
    assert extract_object_key("https://example.com/some/other.png") is None


# --------------------------------------------------------------------------- #
# resign_url / rewrite_image_urls_in_text
# --------------------------------------------------------------------------- #

def test_resign_internal_url_is_fresh_signed(monkeypatch):
    _set_presigned(monkeypatch)
    stale = f"https://mybucket.oss-cn-hangzhou.aliyuncs.com/{KEY}?X-Amz-Signature=deadbeef&X-Amz-Expires=1"
    fresh = resign_url(stale)
    assert urlparse(fresh).path.lstrip("/") == KEY
    assert "X-Amz-Signature=deadbeef" not in fresh
    assert "X-Amz-Signature" in fresh


def test_resign_external_url_unchanged(monkeypatch):
    _set_presigned(monkeypatch)
    ext = "https://example.com/cat.png"
    assert resign_url(ext) == ext


def test_rewrite_markdown_resigns_internal_only(monkeypatch):
    _set_presigned(monkeypatch)
    text = (
        f"Image generated successfully.\n\n"
        f"![Generated Image](https://mybucket.oss-cn-hangzhou.aliyuncs.com/{KEY})\n\n"
        f"URL: https://mybucket.oss-cn-hangzhou.aliyuncs.com/{KEY}\n\n"
        f"see also ![ext](https://example.com/cat.png)"
    )
    out = rewrite_image_urls_in_text(text)
    assert "X-Amz-Signature" in out                       # internal links signed
    assert "https://example.com/cat.png" in out           # external untouched
    assert out.count("X-Amz-Signature") == 2              # md + bare URL, external excluded


def test_rewrite_public_mode_is_noop(monkeypatch):
    _set_public(monkeypatch)
    text = f"![img](https://mybucket.oss-cn-hangzhou.aliyuncs.com/{KEY})"
    assert rewrite_image_urls_in_text(text) == text


# --------------------------------------------------------------------------- #
# ChatResponse integration
# --------------------------------------------------------------------------- #

def test_chat_response_resigns_content_in_presigned_mode(monkeypatch):
    _set_presigned(monkeypatch)
    content = f"![Generated Image](https://mybucket.oss-cn-hangzhou.aliyuncs.com/{KEY})"
    resp = ChatResponse(id="1", content=content, type="ai")
    assert "X-Amz-Signature" in resp.content


def test_chat_response_noop_public_mode(monkeypatch):
    _set_public(monkeypatch)
    content = f"![Generated Image](https://mybucket.oss-cn-hangzhou.aliyuncs.com/{KEY})"
    resp = ChatResponse(id="1", content=content, type="ai")
    assert resp.content == content


def test_chat_response_non_str_content_untouched(monkeypatch):
    _set_presigned(monkeypatch)
    resp = ChatResponse(id="1", content=[{"type": "text", "text": "hi"}], type="ai")
    assert resp.content == [{"type": "text", "text": "hi"}]
