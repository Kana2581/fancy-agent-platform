import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

import aiofiles
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
    """同步生成 WebP 缩略图，供 save 流程和一次性回填脚本共用。"""
    with Image.open(src_path) as im:
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode else "RGB")
        im.thumbnail((THUMBNAIL_MAX_EDGE, THUMBNAIL_MAX_EDGE))
        im.save(dst_path, format="WEBP", quality=THUMBNAIL_QUALITY, method=4)


async def save_generated_image(data: bytes, ext: str = "png") -> str:
    """
    保存到 upload_dir/generated/YYYY/MM/DD/{uuid}.{ext}
    返回 object_key（相对路径），如 generated/2025/01/01/uuid.png
    同时生成 {file}.thumb.webp 供画廊缩略图使用，失败不影响主流程。
    """
    upload_dir = getattr(settings, "UPLOAD_DIR", "/data/uploads")

    date_str = date.today().strftime("%Y/%m/%d")
    save_dir = Path(upload_dir) / "generated" / date_str
    save_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = save_dir / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(data)

    thumb_path = file_path.with_name(file_path.name + THUMBNAIL_SUFFIX)
    try:
        await asyncio.to_thread(generate_thumbnail, file_path, thumb_path)
    except Exception as exc:
        logger.warning("thumbnail generation failed for %s: %s", file_path, exc)

    return f"generated/{date_str}/{filename}"


def build_image_url(object_key: str) -> str:
    """将 object_key 拼接 OSS_URL 得到完整访问地址"""
    oss_url = getattr(settings, "OSS_URL", "http://localhost:8000")
    return f"{oss_url.rstrip('/')}/{object_key}"


def read_image_size(object_key: str) -> tuple[int | None, int | None]:
    """从已保存的文件读真实宽高，失败返回 (None, None)。

    用于把渲染结果的真实分辨率写入 generated_images 表，避免
    传入的 width/height 缺省值与实际不符。
    """
    upload_dir = getattr(settings, "UPLOAD_DIR", "/data/uploads")
    path = Path(upload_dir) / object_key
    try:
        with Image.open(path) as im:
            w, h = im.size
            return int(w), int(h)
    except Exception as exc:
        logger.warning("read_image_size failed for %s: %s", object_key, exc)
        return None, None


def build_thumbnail_url(object_key: str) -> str:
    """返回缩略图的访问地址（约定 {object_key}.thumb.webp）"""
    oss_url = getattr(settings, "OSS_URL", "http://localhost:8000")
    return f"{oss_url.rstrip('/')}/{object_key}{THUMBNAIL_SUFFIX}"
