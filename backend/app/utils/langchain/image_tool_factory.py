import asyncio
import re
from typing import Optional, Union

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.utils.image.adapter_factory import get_image_adapter
from app.utils.image.base_adapter import BaseImageAdapter, build_image_url, read_image_size
from app.utils.image.local_image_loader import load_image_bytes
from app.utils.langchain.image_reference_context import resolve_image_ref_id


def _sanitize_tool_name(name: str, fallback: str = "image_tool") -> str:
    """Sanitize tool name to meet OpenAI requirements: ^[a-zA-Z0-9_-]{1,64}$"""
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized[:64] if sanitized else fallback


class ImageGenerationInput(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    source_image_id: Optional[Union[str, int]] = None
    source_image_url: Optional[str] = None
    source_object_key: Optional[str] = None
    extra: Optional[dict] = None


async def _save_image_to_history(
    *,
    user_id: int,
    image_tool_id: Optional[int],
    provider: str,
    model_name: str,
    prompt: str,
    revised_prompt: Optional[str],
    object_key: str,
    width: int,
    height: int,
    is_img2img: bool,
) -> None:
    try:
        from app.deps.db import get_db_session
        from app.mappers.generated_image_mapper import GeneratedImageMapper
        async with get_db_session() as db:
            await GeneratedImageMapper(db).create_from_dict({
                "user_id": user_id,
                "image_tool_id": image_tool_id,
                "provider": provider,
                "model_name": model_name,
                "prompt": prompt,
                "revised_prompt": revised_prompt,
                "object_key": object_key,
                "width": width,
                "height": height,
                "is_img2img": is_img2img,
            })
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to save generated image to history: {e}")


def build_image_tool_from_config(config: dict, *, user_id: Optional[int] = None) -> StructuredTool:
    provider = config["provider"]
    image_tool_id: Optional[int] = config.get("id")
    model_name: str = config.get("model") or config.get("name", "")
    support_img2img = bool(config.get("support_img2img", False))
    adapter_config = {
        "api_key": config.get("api_key", ""),
        "base_url": config.get("base_url"),
        "model": config.get("model"),
        "default_size": config.get("default_size"),
        "default_quality": config.get("default_quality"),
        "default_style": config.get("default_style"),
        "extra_params": config.get("extra_params") or {},
    }

    async def generate_image(
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        source_image_id: Optional[Union[str, int]] = None,
        source_image_url: Optional[str] = None,
        source_object_key: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> str:
        adapter = get_image_adapter(provider, adapter_config)
        merged_extra = {**(adapter_config.get("extra_params") or {}), **(extra or {})}
        is_img2img = bool(source_image_id or source_image_url or source_object_key)
        if source_image_id:
            image_ref = resolve_image_ref_id(source_image_id)
            if not image_ref:
                raise ValueError(f"Unknown image reference: {source_image_id}")
            source_object_key = image_ref.object_key
            source_image_url = None

        if is_img2img:
            if not support_img2img:
                raise ValueError("This tool does not support image editing")
            if type(adapter).img2img is BaseImageAdapter.img2img:
                raise ValueError(f"Provider '{provider}' does not support image editing")
            source_image_bytes, _mime = await load_image_bytes(
                image_url=source_image_url,
                object_key=source_object_key,
            )
            object_key, revised_prompt = await adapter.img2img(
                image_bytes=source_image_bytes,
                prompt=prompt,
                negative_prompt=negative_prompt or "",
                width=width,
                height=height,
                extra=merged_extra,
            )
        else:
            object_key, revised_prompt = await adapter.generate(
                prompt=prompt,
                negative_prompt=negative_prompt or "",
                width=width,
                height=height,
                extra=merged_extra,
            )
        url = build_image_url(object_key)
        if user_id:
            real_w, real_h = await asyncio.to_thread(read_image_size, object_key)
            await _save_image_to_history(
                user_id=user_id,
                image_tool_id=image_tool_id,
                provider=provider,
                model_name=model_name,
                prompt=prompt,
                revised_prompt=revised_prompt,
                object_key=object_key,
                width=real_w if real_w is not None else (width or 1024),
                height=real_h if real_h is not None else (height or 1024),
                is_img2img=is_img2img,
            )
        result = f"Image generated successfully.\n\n![Generated Image]({url})\n\nURL: {url}"
        if revised_prompt:
            result += f"\nRevised prompt: {revised_prompt}"
        return result

    description = config.get("description") or f"Generate image using {config['name']}"
    if support_img2img:
        description += (
            ". For image editing from the conversation, pass source_image_id from "
            "the image reference list with prompt. source_image_url and "
            "source_object_key are still supported for explicit references."
        )

    tool_name = _sanitize_tool_name(config["name"], fallback=f"{provider}_image_tool")
    return StructuredTool.from_function(
        coroutine=generate_image,
        name=tool_name,
        description=description,
        args_schema=ImageGenerationInput,
    )
