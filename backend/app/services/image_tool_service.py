from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.image_tool_mapper import ImageToolMapper
from app.models.image_tool import ImageTool
from app.schemas.image_tool_schema import (
    GenerateRequest,
    GenerateResponse,
)
from app.utils.image.adapter_factory import get_image_adapter
from app.utils.image.base_adapter import BaseImageAdapter, build_image_url
from app.utils.image.local_image_loader import load_image_bytes


class ImageToolService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = ImageToolMapper(db=db)

    @staticmethod
    def _merge_extra(default_extra: Optional[Dict[str, Any]], request_extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {**(default_extra or {}), **(request_extra or {})}

    @staticmethod
    def _assert_img2img_supported(tool: ImageTool, adapter: Any) -> None:
        if not tool.support_img2img:
            raise ValueError("该工具不支持图片编辑")
        if type(adapter).img2img is BaseImageAdapter.img2img:
            raise ValueError(f"provider '{tool.provider}' does not support img2img")

    async def create_tool(self, data: Dict[str, Any]) -> ImageTool:
        tool = await self.mapper.create_from_dict(data)
        await self.db.commit()
        return tool

    async def get_tool(self, tool_id: int) -> Optional[ImageTool]:
        return await self.mapper.get_by_id(tool_id)

    async def list_tools_by_user(
        self, user_id: int, offset: int = 0, limit: int = 100
    ) -> List[ImageTool]:
        return await self.mapper.list_by_filters({"user_id": user_id}, offset, limit)

    async def update_tool(self, tool_id: int, data: Dict[str, Any]) -> Optional[ImageTool]:
        tool = await self.mapper.update_by_id(tool_id, data)
        await self.db.commit()
        return tool

    async def delete_tool(self, tool_id: int) -> bool:
        result = await self.mapper.delete_by_id(tool_id)
        await self.db.commit()
        return result

    async def generate(
        self, tool_id: int, user_id: int, req: GenerateRequest
    ) -> tuple[GenerateResponse, "ImageTool", str]:
        tool = await self.mapper.get_by_id(tool_id)
        if not tool or tool.user_id != user_id:
            raise ValueError("Image tool not found")

        config = {
            "api_key": tool.api_key,
            "base_url": tool.base_url,
            "model": tool.model,
            "default_size": tool.default_size,
            "default_quality": tool.default_quality,
            "default_style": tool.default_style,
            "extra_params": tool.extra_params,
        }

        adapter = get_image_adapter(tool.provider, config)
        merged_extra = self._merge_extra(tool.extra_params, req.extra)
        object_key, revised_prompt = await adapter.generate(
            req.prompt,
            req.negative_prompt,
            req.width,
            req.height,
            merged_extra,
        )
        image_url = build_image_url(object_key)
        return GenerateResponse(image_url=image_url, revised_prompt=revised_prompt), tool, object_key

    async def img2img(
        self,
        tool_id: int,
        user_id: int,
        image_bytes: bytes,
        prompt: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
        negative_prompt: str = "",
    ) -> tuple[GenerateResponse, "ImageTool", str]:
        tool = await self.mapper.get_by_id(tool_id)
        if not tool or tool.user_id != user_id:
            raise ValueError("Image tool not found")

        config = {
            "api_key": tool.api_key,
            "base_url": tool.base_url,
            "model": tool.model,
            "default_size": tool.default_size,
            "default_quality": tool.default_quality,
            "default_style": tool.default_style,
            "extra_params": tool.extra_params,
        }

        adapter = get_image_adapter(tool.provider, config)
        self._assert_img2img_supported(tool, adapter)
        merged_extra = self._merge_extra(tool.extra_params, extra)
        object_key, revised_prompt = await adapter.img2img(
            image_bytes=image_bytes,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            extra=merged_extra,
        )
        image_url = build_image_url(object_key)
        return GenerateResponse(image_url=image_url, revised_prompt=revised_prompt), tool, object_key

    async def img2img_from_reference(
        self,
        tool_id: int,
        user_id: int,
        prompt: str,
        image_url: Optional[str] = None,
        object_key: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
        negative_prompt: str = "",
    ) -> tuple[GenerateResponse, "ImageTool", str]:
        image_bytes, _mime = await load_image_bytes(
            image_url=image_url,
            object_key=object_key,
        )
        return await self.img2img(
            tool_id=tool_id,
            user_id=user_id,
            image_bytes=image_bytes,
            prompt=prompt,
            width=width,
            height=height,
            extra=extra,
            negative_prompt=negative_prompt,
        )

