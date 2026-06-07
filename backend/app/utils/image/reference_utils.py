import base64
import io

import httpx
from PIL import Image, UnidentifiedImageError

DEFAULT_DOWNLOAD_TIMEOUT = 60.0
DEFAULT_MAX_IMAGE_BYTES = 20 * 1024 * 1024


def _validate_image_bytes(data: bytes) -> None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Referenced file is not a valid image") from exc


async def download_image_bytes(
    url: str,
    timeout: float = DEFAULT_DOWNLOAD_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
) -> bytes:
    if url.startswith("data:"):
        header, _, encoded = url.partition(",")
        if ";base64" not in header:
            raise ValueError("Only base64-encoded data URIs are supported")
        image_bytes = base64.b64decode(encoded)
        if len(image_bytes) > max_bytes:
            raise ValueError(f"Referenced image exceeds {max_bytes} bytes")
        _validate_image_bytes(image_bytes)
        return image_bytes

    chunks: list[bytes] = []
    total = 0
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                content_type = (response.headers.get("content-type") or "").lower()
                if content_type and not content_type.startswith("image/"):
                    raise ValueError(f"Referenced URL is not an image: {content_type}")

                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"Referenced image exceeds {max_bytes} bytes")
                    chunks.append(chunk)
    except httpx.HTTPError as exc:
        raise ValueError(f"Failed to download source image: {exc}") from exc

    image_bytes = b"".join(chunks)
    _validate_image_bytes(image_bytes)
    return image_bytes
