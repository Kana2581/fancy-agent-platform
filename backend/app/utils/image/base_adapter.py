import asyncio
import io
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

THUMBNAIL_MAX_EDGE = 512
THUMBNAIL_QUALITY = 80
THUMBNAIL_SUFFIX = ".thumb.webp"


class BaseImageAdapter(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, str | None]:
        """生成图片，返回 (本地 OSS URL, revised_prompt)"""

    async def img2img(
        self,
        image_bytes: bytes,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, str | None]:
        raise NotImplementedError("img2img is not supported by this image adapter")


def parse_size_dims(size: str | None, sep_priority: tuple[str, ...] = ("x", "*")) -> tuple[int, int]:
    """把 '1024x1024' / '1024*1024' 这类字符串解析成 (w, h)，解析失败回退 1024。"""
    if not size:
        return 1024, 1024
    for sep in sep_priority:
        if sep in size:
            try:
                a, b = size.split(sep, 1)
                return int(a.strip()), int(b.strip())
            except (ValueError, TypeError):
                return 1024, 1024
    return 1024, 1024


def generate_thumbnail(src_path: Path, dst_path: Path) -> None:
    """同步生成 WebP 缩略图（供磁盘路径场景和回填脚本使用）。"""
    with Image.open(src_path) as im:
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode else "RGB")
        im.thumbnail((THUMBNAIL_MAX_EDGE, THUMBNAIL_MAX_EDGE))
        im.save(dst_path, format="WEBP", quality=THUMBNAIL_QUALITY, method=4)


def _generate_thumbnail_bytes(data: bytes) -> bytes:
    """从内存 bytes 生成 WebP 缩略图，不触碰磁盘。"""
    buf = io.BytesIO()
    with Image.open(io.BytesIO(data)) as im:
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode else "RGB")
        im.thumbnail((THUMBNAIL_MAX_EDGE, THUMBNAIL_MAX_EDGE))
        im.save(buf, format="WEBP", quality=THUMBNAIL_QUALITY, method=4)
    return buf.getvalue()


async def save_generated_image(data: bytes, ext: str = "png") -> str:
    """
    保存到 generated/YYYY/MM/DD/{uuid}.{ext}，同时保存缩略图。
    返回 object_key，如 generated/2025/01/01/uuid.png。
    本地模式写磁盘；S3 模式写对象存储，均通过存储工厂路由。
    """
    from app.services.storage import get_file_uploader

    date_str = date.today().strftime("%Y/%m/%d")
    filename = f"{uuid.uuid4().hex}.{ext}"
    object_key = f"generated/{date_str}/{filename}"

    uploader = get_file_uploader()
    await uploader.save_raw_bytes(data, object_key)

    try:
        thumb_bytes = await asyncio.to_thread(_generate_thumbnail_bytes, data)
        await uploader.save_raw_bytes(thumb_bytes, f"{object_key}{THUMBNAIL_SUFFIX}")
    except Exception as exc:
        logger.warning("thumbnail generation failed for %s: %s", object_key, exc)

    return object_key


def build_image_url(object_key: str) -> str:
    """由 object_key 生成完整访问地址（public 模式明文拼接，presigned 模式签名 URL）"""
    from app.services.storage.url_signer import build_storage_url

    return build_storage_url(object_key)


def read_image_size(object_key: str) -> tuple[int | None, int | None]:
    """从已保存的文件读真实宽高，失败返回 (None, None)。

    本地模式直接读磁盘；S3 模式本地文件不存在时回退到 HTTP GET 公网 URL。
    调用方已用 asyncio.to_thread，此处同步 I/O 是正确的。
    """
    upload_dir = getattr(settings, "UPLOAD_DIR", "/data/uploads")
    path = Path(upload_dir) / object_key
    if path.is_file():
        try:
            with Image.open(path) as im:
                return int(im.size[0]), int(im.size[1])
        except Exception as exc:
            logger.warning("read_image_size local failed for %s: %s", object_key, exc)

    # S3 模式兜底：从公网 URL 下载（bucket 须为 public-read）
    try:
        import httpx
        resp = httpx.get(build_image_url(object_key), timeout=30)
        resp.raise_for_status()
        with Image.open(io.BytesIO(resp.content)) as im:
            return int(im.size[0]), int(im.size[1])
    except Exception as exc:
        logger.warning("read_image_size remote failed for %s: %s", object_key, exc)
        return None, None


def build_thumbnail_url(object_key: str) -> str:
    """返回缩略图的访问地址（约定 {object_key}.thumb.webp）"""
    from app.services.storage.url_signer import build_storage_url

    return build_storage_url(f"{object_key}{THUMBNAIL_SUFFIX}")
