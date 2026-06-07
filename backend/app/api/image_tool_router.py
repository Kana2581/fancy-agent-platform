import asyncio
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

from app.deps.service import get_image_tool_service, get_generated_image_service
from app.deps.user import get_current_user
from app.schemas.image_tool_schema import (
    ImageToolCreate,
    ImageToolOut,
    ImageToolUpdate,
    GenerateRequest,
    GenerateResponse,
    Img2ImgRefRequest,
)
from app.services.image_tool_service import ImageToolService
from app.services.generated_image_service import GeneratedImageService
from app.utils.image.base_adapter import read_image_size
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/image-tools", tags=["Image Tools"])


def _status_code_from_value_error(error: ValueError) -> int:
    message = str(error)
    if message == "Image tool not found":
        return 404
    return 400


@router.post("", response_model=ImageToolOut)
async def create_image_tool(
    data: ImageToolCreate,
    service: ImageToolService = Depends(get_image_tool_service),
    user_id: int = Depends(get_current_user),
):
    payload = data.model_dump()
    payload["user_id"] = user_id
    return await service.create_tool(payload)


@router.get("", response_model=List[ImageToolOut])
async def list_image_tools(
    offset: int = 0,
    limit: int = 100,
    service: ImageToolService = Depends(get_image_tool_service),
    user_id: int = Depends(get_current_user),
):
    return await service.list_tools_by_user(user_id, offset, limit)


@router.get("/{tool_id}", response_model=ImageToolOut)
async def get_image_tool(
    tool_id: int,
    service: ImageToolService = Depends(get_image_tool_service),
    user_id: int = Depends(get_current_user),
):
    tool = await service.get_tool(tool_id)
    if not tool or tool.user_id != user_id:
        raise HTTPException(status_code=404, detail="Image tool not found")
    return tool


@router.put("/{tool_id}", response_model=ImageToolOut)
async def update_image_tool(
    tool_id: int,
    data: ImageToolUpdate,
    service: ImageToolService = Depends(get_image_tool_service),
    user_id: int = Depends(get_current_user),
):
    tool = await service.get_tool(tool_id)
    if not tool or tool.user_id != user_id:
        raise HTTPException(status_code=404, detail="Image tool not found")
    updated = await service.update_tool(tool_id, data.model_dump(exclude_none=True))
    return updated


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_tool(
    tool_id: int,
    service: ImageToolService = Depends(get_image_tool_service),
    user_id: int = Depends(get_current_user),
):
    tool = await service.get_tool(tool_id)
    if not tool or tool.user_id != user_id:
        raise HTTPException(status_code=404, detail="Image tool not found")
    await service.delete_tool(tool_id)


@router.post("/{tool_id}/generate", response_model=GenerateResponse)
async def generate_image(
    tool_id: int,
    req: GenerateRequest,
    service: ImageToolService = Depends(get_image_tool_service),
    gen_img_service: GeneratedImageService = Depends(get_generated_image_service),
    user_id: int = Depends(get_current_user),
):
    try:
        result, tool, object_key = await service.generate(tool_id, user_id, req)
        try:
            real_w, real_h = await asyncio.to_thread(read_image_size, object_key)
            await gen_img_service.create({
                "user_id": user_id,
                "image_tool_id": tool_id,
                "provider": tool.provider,
                "model_name": tool.model or "",
                "prompt": req.prompt,
                "revised_prompt": result.revised_prompt,
                "object_key": object_key,
                "width": real_w if real_w is not None else req.width,
                "height": real_h if real_h is not None else req.height,
                "is_img2img": False,
            })
        except Exception as persist_exc:
            logger.warning("failed to persist generated_image: %s", persist_exc)
        return result
    except ValueError as e:
        raise HTTPException(status_code=_status_code_from_value_error(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片生成失败: {str(e)}")


@router.post("/{tool_id}/img2img", response_model=GenerateResponse)
async def img2img(
    tool_id: int,
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: int | None = Form(None),
    height: int | None = Form(None),
    extra: str | None = Form(None),
    image: UploadFile = File(...),
    service: ImageToolService = Depends(get_image_tool_service),
    gen_img_service: GeneratedImageService = Depends(get_generated_image_service),
    user_id: int = Depends(get_current_user),
):
    try:
        parsed_extra = {}
        if extra:
            try:
                parsed_extra = json.loads(extra)
            except json.JSONDecodeError as exc:
                raise ValueError("extra must be valid JSON string") from exc

        image_bytes = await image.read()
        result, tool, object_key = await service.img2img(
            tool_id=tool_id,
            user_id=user_id,
            image_bytes=image_bytes,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            extra=parsed_extra,
        )
        try:
            real_w, real_h = await asyncio.to_thread(read_image_size, object_key)
            await gen_img_service.create({
                "user_id": user_id,
                "image_tool_id": tool_id,
                "provider": tool.provider,
                "model_name": tool.model or "",
                "prompt": prompt,
                "revised_prompt": result.revised_prompt,
                "object_key": object_key,
                "width": real_w if real_w is not None else width,
                "height": real_h if real_h is not None else height,
                "is_img2img": True,
            })
        except Exception as persist_exc:
            logger.warning("failed to persist generated_image: %s", persist_exc)
        return result
    except ValueError as e:
        raise HTTPException(status_code=_status_code_from_value_error(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片编辑失败: {str(e)}")


@router.post("/{tool_id}/img2img/ref", response_model=GenerateResponse)
async def img2img_by_reference(
    tool_id: int,
    req: Img2ImgRefRequest,
    service: ImageToolService = Depends(get_image_tool_service),
    gen_img_service: GeneratedImageService = Depends(get_generated_image_service),
    user_id: int = Depends(get_current_user),
):
    try:
        result, tool, object_key = await service.img2img_from_reference(
            tool_id=tool_id,
            user_id=user_id,
            prompt=req.prompt,
            image_url=req.image_url,
            object_key=req.object_key,
            negative_prompt=req.negative_prompt,
            width=req.width,
            height=req.height,
            extra=req.extra,
        )
        try:
            real_w, real_h = await asyncio.to_thread(read_image_size, object_key)
            await gen_img_service.create({
                "user_id": user_id,
                "image_tool_id": tool_id,
                "provider": tool.provider,
                "model_name": tool.model or "",
                "prompt": req.prompt,
                "revised_prompt": result.revised_prompt,
                "object_key": object_key,
                "width": real_w if real_w is not None else req.width,
                "height": real_h if real_h is not None else req.height,
                "is_img2img": True,
            })
        except Exception as persist_exc:
            logger.warning("failed to persist generated_image: %s", persist_exc)
        return result
    except ValueError as e:
        raise HTTPException(status_code=_status_code_from_value_error(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片编辑失败: {str(e)}")

