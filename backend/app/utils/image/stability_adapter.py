import base64
from typing import Optional

import httpx

from app.utils.image.base_adapter import BaseImageAdapter, parse_size_dims, save_generated_image


STABILITY_API_BASE = "https://api.stability.ai"


class StabilityAIImageAdapter(BaseImageAdapter):
    def __init__(self, config: dict):
        self.api_key = config.get("api_key", "")
        self.engine_id = config.get("model") or "stable-diffusion-xl-1024-v1-0"
        self.default_size = config.get("default_size") or "1024x1024"
        extra_params = config.get("extra_params") or {}
        self.cfg_scale = extra_params.get("cfg_scale", 7)
        self.steps = extra_params.get("steps", 30)

    def _resolve_dims(self, width: int | None, height: int | None) -> tuple[int, int]:
        if width and height:
            return width, height
        return parse_size_dims(self.default_size)

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, Optional[str]]:
        extra = extra or {}
        url = f"{STABILITY_API_BASE}/v1/generation/{self.engine_id}/text-to-image"

        text_prompts = [{"text": prompt, "weight": 1.0}]
        if negative_prompt:
            text_prompts.append({"text": negative_prompt, "weight": -1.0})

        w, h = self._resolve_dims(width, height)
        payload = {
            "text_prompts": text_prompts,
            "cfg_scale": extra.get("cfg_scale", self.cfg_scale),
            "steps": extra.get("steps", self.steps),
            "width": w,
            "height": h,
            "samples": 1,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        artifact = data["artifacts"][0]
        image_bytes = base64.b64decode(artifact["base64"])
        object_key = await save_generated_image(image_bytes, "png")
        return object_key, None

    async def img2img(
        self,
        image_bytes: bytes,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, Optional[str]]:
        extra = extra or {}
        url = f"{STABILITY_API_BASE}/v1/generation/{self.engine_id}/image-to-image"

        text_prompts = [{"text": prompt, "weight": 1.0}]
        if negative_prompt:
            text_prompts.append({"text": negative_prompt, "weight": -1.0})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        import io
        files = {"init_image": ("image.png", io.BytesIO(image_bytes), "image/png")}
        form_data = {
            "image_strength": str(extra.get("image_strength", 0.35)),
            "init_image_mode": "IMAGE_STRENGTH",
            "cfg_scale": str(extra.get("cfg_scale", self.cfg_scale)),
            "steps": str(extra.get("steps", self.steps)),
            "samples": "1",
        }
        for i, tp in enumerate(text_prompts):
            form_data[f"text_prompts[{i}][text]"] = tp["text"]
            form_data[f"text_prompts[{i}][weight]"] = str(tp["weight"])

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, data=form_data, files=files, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        artifact = data["artifacts"][0]
        image_bytes_result = base64.b64decode(artifact["base64"])
        object_key = await save_generated_image(image_bytes_result, "png")
        return object_key, None
