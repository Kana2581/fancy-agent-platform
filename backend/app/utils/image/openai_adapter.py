import base64
import io
from typing import Optional

import httpx
from openai import AsyncOpenAI
from PIL import Image, UnidentifiedImageError

from app.utils.image.base_adapter import BaseImageAdapter, save_generated_image

_ALLOWED_EDIT_SIZES = {"1024x1024", "1536x1024", "1024x1536", "auto"}
_ALLOWED_GEN_SIZES = {"1024x1024", "1024x1792", "1792x1024"}
_DALLE_MODELS = {"dall-e-2", "dall-e-3"}
# OpenAI edits 接受 PNG / JPEG / WEBP，其他格式统一转 PNG
_OPENAI_EDIT_FORMATS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}


def _clamp_size(size: str, allowed: set, fallback: str) -> str:
    return size if size in allowed else fallback


def _normalize_edit_image(image_bytes: bytes) -> tuple[bytes, str]:
    """探测真实图片格式并返回 (bytes, ext)。

    避免把 JPEG/WebP 以 image.png 名义传给 OpenAI 导致 400。
    解析失败或非 PNG/JPEG/WEBP 时统一转 PNG。
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            fmt = (im.format or "").upper()
            if fmt in _OPENAI_EDIT_FORMATS:
                return image_bytes, _OPENAI_EDIT_FORMATS[fmt]
            buf = io.BytesIO()
            mode = "RGBA" if "A" in im.mode else "RGB"
            im.convert(mode).save(buf, format="PNG")
            return buf.getvalue(), "png"
    except (UnidentifiedImageError, OSError):
        return image_bytes, "png"


class OpenAIImageAdapter(BaseImageAdapter):
    def __init__(self, config: dict):
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url") or None
        self.model = config.get("model") or "dall-e-3"
        self.default_size = config.get("default_size") or "1024x1024"
        self.default_quality = config.get("default_quality") or "standard"
        self.default_style = config.get("default_style") or "vivid"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, Optional[str]]:
        extra = extra or {}
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        raw_size = extra.get("size") or (
            f"{width}x{height}" if width and height else self.default_size
        )
        size = _clamp_size(raw_size, _ALLOWED_GEN_SIZES, "1024x1024") if self.model == "dall-e-3" else raw_size
        quality = extra.get("quality") or self.default_quality
        style = extra.get("style") or self.default_style

        kwargs: dict = dict(
            model=self.model,
            prompt=prompt,
            n=1,
            size=size,
        )
        # dall-e-2/3 支持 response_format，gpt-image-1 不接受该参数（只返 b64_json）
        if self.model in _DALLE_MODELS:
            kwargs["response_format"] = "url"
        if self.model == "dall-e-3":
            kwargs["quality"] = quality
            kwargs["style"] = style

        response = await client.images.generate(**kwargs)
        image_data = response.data[0]

        revised_prompt: Optional[str] = getattr(image_data, "revised_prompt", None)
        image_b64: Optional[str] = getattr(image_data, "b64_json", None)
        image_url_remote: Optional[str] = getattr(image_data, "url", None)

        if image_b64:
            image_bytes = base64.b64decode(image_b64)
        elif image_url_remote:
            async with httpx.AsyncClient(timeout=180) as http:
                resp = await http.get(image_url_remote)
                resp.raise_for_status()
                image_bytes = resp.content
        else:
            raise RuntimeError("OpenAI image API returned neither b64_json nor url")

        object_key = await save_generated_image(image_bytes, "png")
        return object_key, revised_prompt

    async def img2img(
        self,
        image_bytes: bytes,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, Optional[str]]:
        del negative_prompt
        extra = extra or {}

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        raw_size = extra.get("size") or (
            f"{width}x{height}" if width and height else self.default_size
        )
        size = _clamp_size(raw_size, _ALLOWED_EDIT_SIZES, "auto")
        model = extra.get("model") or self.model or "gpt-image-1"
        if model == "dall-e-3":
            model = "gpt-image-1"
        quality = extra.get("quality")
        input_fidelity = extra.get("input_fidelity")
        background = extra.get("background")
        output_format = extra.get("output_format", "png")
        output_compression = extra.get("output_compression")

        normalized_bytes, upload_ext = _normalize_edit_image(image_bytes)
        image_io = io.BytesIO(normalized_bytes)
        image_io.name = f"image.{upload_ext}"

        kwargs = dict(
            image=image_io,
            prompt=prompt,
            n=1,
            model=model,
        )
        if size:
            kwargs["size"] = size
        if quality:
            kwargs["quality"] = quality
        if input_fidelity:
            kwargs["input_fidelity"] = input_fidelity
        if background:
            kwargs["background"] = background
        if output_format and output_format != "png":
            kwargs["output_format"] = output_format
        if output_compression is not None:
            kwargs["output_compression"] = output_compression

        response = await client.images.edit(**kwargs)
        image_data = response.data[0]
        revised_prompt: Optional[str] = getattr(image_data, "revised_prompt", None)
        image_b64: Optional[str] = getattr(image_data, "b64_json", None)

        if image_b64:
            image_bytes_result = base64.b64decode(image_b64)
        else:
            image_url_remote = image_data.url
            async with httpx.AsyncClient(timeout=180) as http:
                resp = await http.get(image_url_remote)
                resp.raise_for_status()
                image_bytes_result = resp.content

        object_key = await save_generated_image(image_bytes_result, "png")
        return object_key, revised_prompt
