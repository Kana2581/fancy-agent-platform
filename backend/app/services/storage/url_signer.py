"""Centralised storage URL construction.

Single source of truth for turning an `object_key` into an access URL, and the
inverse — recovering an `object_key` from a URL we previously produced.

Two modes (S3 backend only; `local` is always public):
- **public** (default): `OSS_URL/{object_key}` — permanent, world-readable.
- **presigned**: a signed, expiring GET URL against a private bucket.

Presigning is a *local* crypto operation (no network I/O), so these helpers stay
synchronous and can be called from sync sites (Pydantic computed fields, markdown
builders) without going async.

The staleness problem (a presigned URL frozen into chat history) is solved by
`extract_object_key` + `resign_url`: the path component of one of our URLs is the
object_key and never changes — only the `?...signature` part expires — so any of
our URLs can be re-signed on read, regardless of whether its signature is stale.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)


def _presign_enabled() -> bool:
    return (
        getattr(settings, "STORAGE_BACKEND", "local").lower() == "s3"
        and getattr(settings, "S3_URL_MODE", "public").lower() == "presigned"
    )


def _public_url(object_key: str) -> str:
    oss = (settings.OSS_URL or "").rstrip("/")
    return f"{oss}/{object_key.lstrip('/')}"


@lru_cache(maxsize=1)
def _signer_client():
    """A cached *synchronous* botocore S3 client used only for presigning.

    botocore ships transitively via aioboto3 → aiobotocore, so no new dependency.
    `generate_presigned_url` does no network I/O, so a sync client is fine here.
    """
    import botocore.session
    from botocore.client import Config

    session = botocore.session.get_session()
    return session.create_client(
        "s3",
        endpoint_url=(settings.S3_ENDPOINT_URL or None),
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def build_storage_url(object_key: str) -> str:
    """Turn an object_key into an access URL honouring the configured S3 URL mode.

    - public mode / local backend → plain `OSS_URL/{object_key}` (unchanged behaviour)
    - presigned mode → a signed, expiring GET URL
    """
    if not object_key:
        return object_key
    key = object_key.lstrip("/")
    if not _presign_enabled():
        return _public_url(key)
    try:
        return _signer_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=int(getattr(settings, "S3_PRESIGN_EXPIRE", 3600)),
        )
    except Exception:
        logger.exception("presign failed for object_key=%s; falling back to public URL", key)
        return _public_url(key)


def _our_hosts() -> set[str]:
    hosts: set[str] = set()
    for raw in (settings.OSS_URL, getattr(settings, "S3_ENDPOINT_URL", "")):
        if raw:
            h = urlparse(raw).netloc
            if h:
                hosts.add(h)
                # virtual-hosted presigned URLs prepend the bucket to the endpoint host
                bucket = getattr(settings, "S3_BUCKET", "")
                if bucket and not h.startswith(f"{bucket}."):
                    hosts.add(f"{bucket}.{h}")
    return hosts


def extract_object_key(url: str) -> Optional[str]:
    """Recover the object_key from a URL we produced, or None if it's external.

    The query string (which carries any expiring signature) is dropped — only the
    path matters, and the path is the object_key. This is what makes stale
    presigned URLs in stored content recoverable.
    """
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    candidate = (parsed.path or "").lstrip("/")
    if not candidate:
        return None
    if parsed.netloc in _our_hosts():
        return candidate
    # Fallback: path matches a file under UPLOAD_DIR (tolerates scheme/host drift, local mode)
    try:
        if (Path(settings.UPLOAD_DIR) / candidate).is_file():
            return candidate
    except OSError:
        pass
    return None


def resign_url(url: str) -> str:
    """Re-sign one of our URLs with a fresh signature; pass through external URLs."""
    key = extract_object_key(url)
    if key is None:
        return url
    return build_storage_url(key)


# markdown ![alt](url)  和  纯文本 "URL: https://..." 两种内联形式
_MD_IMG_RE = re.compile(r"(!\[[^\]]*\]\()\s*(https?://[^\s)]+)(\))")
_BARE_URL_RE = re.compile(r"(URL:\s*)(https?://\S+)")


def rewrite_image_urls_in_text(text: str) -> str:
    """Re-sign every internal image URL embedded in markdown/plain text.

    No-op in public mode (resign returns the same public URL) and for external URLs.
    """
    if not text or "http" not in text:
        return text

    def _md(m: re.Match) -> str:
        return f"{m.group(1)}{resign_url(m.group(2))}{m.group(3)}"

    def _bare(m: re.Match) -> str:
        return f"{m.group(1)}{resign_url(m.group(2))}"

    return _BARE_URL_RE.sub(_bare, _MD_IMG_RE.sub(_md, text))
