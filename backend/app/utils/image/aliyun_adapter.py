import base64

import httpx

from app.utils.image.base_adapter import BaseImageAdapter, save_generated_image

API_PATH = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


class AliyunImageAdapter(BaseImageAdapter):

    def __init__(self, config: dict):
        self.api_key = config.get("api_key", "")
        self.model = config.get("model") or "qwen-image-2.0-pro"
        self.default_size = config.get("default_size") or "2048*2048"
        self.url = API_PATH

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, str | None]:
        extra = extra or {}
        size = f"{width}*{height}" if (width and height) else self.default_size

        parameters: dict = {"size": size}
        if negative_prompt:
            parameters["negative_prompt"] = negative_prompt

        payload = {
            "model": self.model,
            "input": {
                "messages": [{"role": "user", "content": [{"text": prompt}]}]
            },
            "parameters": parameters,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(self.url, headers=headers, json=payload)

        try:
            data = r.json()
        except Exception:
            r.raise_for_status()
            raise

        if r.status_code != 200 or data.get("code"):
            code = data.get("code") or str(r.status_code)
            msg = data.get("message") or r.text
            raise RuntimeError(f"Aliyun API error: {code} - {msg}")

        image_url = data["output"]["choices"][0]["message"]["content"][0]["image"]

        async with httpx.AsyncClient(timeout=60) as client:
            img_r = await client.get(image_url)
            img_r.raise_for_status()

        object_key = await save_generated_image(img_r.content, "png")
        return object_key, None

    async def img2img(
        self,
        image_bytes: bytes,
        prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        extra: dict | None = None,
    ) -> tuple[str, str | None]:
        extra = extra or {}
        size = f"{width}*{height}" if (width and height) else self.default_size

        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_uri = f"data:image/png;base64,{b64}"

        # adapter 契约只返回单图，强制 n=1，避免用户传 n>1 后多余结果被静默丢弃
        parameters: dict = {
            "size": size,
            "n": 1,
            "prompt_extend": extra.get("prompt_extend", True),
            "watermark": extra.get("watermark", False),
        }
        if negative_prompt:
            parameters["negative_prompt"] = negative_prompt

        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": data_uri},
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": parameters,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(self.url, headers=headers, json=payload)

        try:
            data = r.json()
        except Exception:
            r.raise_for_status()
            raise

        if r.status_code != 200 or data.get("code"):
            code = data.get("code") or str(r.status_code)
            msg = data.get("message") or r.text
            raise RuntimeError(f"Aliyun API error: {code} - {msg}")

        image_url = data["output"]["choices"][0]["message"]["content"][0]["image"]

        async with httpx.AsyncClient(timeout=60) as client:
            img_r = await client.get(image_url)
            img_r.raise_for_status()

        object_key = await save_generated_image(img_r.content, "png")
        return object_key, None