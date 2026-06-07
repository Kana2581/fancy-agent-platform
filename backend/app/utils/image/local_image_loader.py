"""Local-first image loading.

Centralises how the backend converts an `object_key` / internal `OSS_URL`
into raw bytes + a mime_type, so the LLM input pipeline never depends on
the file being publicly fetchable.

External URLs (anything that doesn't point back at our own `OSS_URL`) still
go through the legacy HTTP downloader so that user-supplied or third-party
image references keep working.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.core.config import settings
from app.utils.image.reference_utils import _validate_image_bytes, download_image_bytes

_EXT_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".svg": "image/svg+xml",
}

_DEFAULT_MIME = "image/png"


def mime_from_ext(ext_or_path: str) -> str:
    """Return a mime_type for the given extension or path, defaulting to image/png."""
    ext = Path(ext_or_path).suffix.lower() if ext_or_path else ""
    return _EXT_TO_MIME.get(ext, _DEFAULT_MIME)


def _upload_root() -> Path:
    return Path(settings.UPLOAD_DIR)


def _normalize_object_key(object_key: str) -> str:
    return object_key.strip().lstrip("/")


def strip_oss_prefix(url: str) -> Optional[str]:
    """If `url` points back at our own OSS_URL, return the relative object_key.

    Returns None when the URL is external — caller should fall back to HTTP.
    """
    if not url:
        return None
    oss = (settings.OSS_URL or "").rstrip("/")
    if oss and url.startswith(oss + "/"):
        return url[len(oss) + 1 :]

    # Also tolerate scheme/host mismatches: if the path component matches an
    # existing file under UPLOAD_DIR, treat it as internal.
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.path:
        candidate = parsed.path.lstrip("/")
        if candidate and (_upload_root() / candidate).is_file():
            return candidate
    return None


def read_local_image(object_key: str) -> Tuple[bytes, str]:
    """Read an image stored under UPLOAD_DIR. Raises FileNotFoundError if missing."""
    key = _normalize_object_key(object_key)
    if not key:
        raise ValueError("object_key is empty")

    path = _upload_root() / key
    resolved = path.resolve()
    root_resolved = _upload_root().resolve()
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"object_key escapes upload root: {object_key}")
    if not resolved.is_file():
        raise FileNotFoundError(f"local image not found: {object_key}")

    data = resolved.read_bytes()
    _validate_image_bytes(data)
    return data, mime_from_ext(resolved.suffix)


async def load_image_bytes(
    *,
    image_url: Optional[str] = None,
    object_key: Optional[str] = None,
) -> Tuple[bytes, str]:
    """Resolve an image reference to (bytes, mime_type).

    Resolution order:
    1. explicit object_key → local disk
    2. image_url that resolves back to our OSS_URL → local disk
    3. data: URI or external http(s) URL → download_image_bytes
    """
    if object_key:
        return await asyncio.to_thread(read_local_image, object_key)

    if image_url:
        url = image_url.strip()
        if not url:
            raise ValueError("image_url is empty")

        if url.startswith("data:"):
            data = await download_image_bytes(url)
            mime = "image/png"
            header = url.split(",", 1)[0]
            if header.startswith("data:") and ";" in header:
                mime = header[5 : header.index(";")] or mime
            return data, mime

        internal_key = strip_oss_prefix(url)
        if internal_key:
            return await asyncio.to_thread(read_local_image, internal_key)

        data = await download_image_bytes(url)
        return data, mime_from_ext(urlparse(url).path)

    raise ValueError("image_url or object_key is required")
