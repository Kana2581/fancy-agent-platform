from typing import Optional

import httpx

from app.utils.image.base_adapter import BaseImageAdapter, save_generated_image

SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/images/generations"


class SiliconFlowImageAdapter(BaseImageAdapter):
    def __init__(self, config: dict):
        self.api_key = config.get("api_key", "")
        self.model = config.get("model") or "stabilityai/stable-diffusion-xl-base-1.0"
        self.default_size = config.get("default_size") or "1024x1024"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, Optional[str]]:
        extra = extra or {}
        size = extra.get("size") or (
            f"{width}x{height}" if width and height else self.default_size
        )

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "image_size": size,
            "batch_size": 1,  # 修复：n → batch_size
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if "num_inference_steps" in extra:
            payload["num_inference_steps"] = extra["num_inference_steps"]
        if "guidance_scale" in extra:
            payload["guidance_scale"] = extra["guidance_scale"]
        if "seed" in extra:
            payload["seed"] = extra["seed"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(SILICONFLOW_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        image_url_remote = data["images"][0]["url"]

        async with httpx.AsyncClient(timeout=60) as client:
            img_resp = await client.get(image_url_remote)
            img_resp.raise_for_status()
            image_bytes = img_resp.content

        object_key = await save_generated_image(image_bytes, "png")
        return object_key, None
