from app.utils.image.aliyun_adapter import AliyunImageAdapter
from app.utils.image.base_adapter import BaseImageAdapter
from app.utils.image.openai_adapter import OpenAIImageAdapter
from app.utils.image.siliconflow_adapter import SiliconFlowImageAdapter
from app.utils.image.stability_adapter import StabilityAIImageAdapter


def get_image_adapter(provider: str, config: dict) -> BaseImageAdapter:
    if provider == "openai":
        return OpenAIImageAdapter(config)
    elif provider == "stability":
        return StabilityAIImageAdapter(config)
    elif provider == "siliconflow":
        return SiliconFlowImageAdapter(config)
    elif provider == "aliyun":
        return AliyunImageAdapter(config)
    raise ValueError(f"Unknown image provider: {provider}")
