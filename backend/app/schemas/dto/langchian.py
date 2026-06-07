from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator
from typing import List
from pydantic import field_validator

_PROVIDER_MAP = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google_genai",
    "google_genai": "google_genai",
    "google_vertexai": "google_vertexai",
    "azure": "azure_openai",
    "azure_openai": "azure_openai",
    "custom": "openai",
    "ollama": "ollama",
    "deepseek": "deepseek",
    "groq": "groq",
    "mistralai": "mistralai",
    "xai": "xai",
    "aliyun": "openai",
}

class ValidChatModel(BaseModel):
    model_provider: str = Field("openai", alias="provider", description="提供商")
    model: str = Field(...,alias="model_name",description="model name")
    base_url: Optional[str] = None
    api_key: Optional[str] = None

    # v2 风格的 pre 验证器，用于把空字符串转换为 None
    @model_validator(mode='before')
    def empty_str_to_none(cls, values: dict) -> dict:
        for field in ['base_url', 'api_key']:
            if field in values and values[field] == "":
                values[field] = None
        return values

    @field_validator("model_provider", mode="before")
    @classmethod
    def normalize_provider(cls, v: str) -> str:
        return _PROVIDER_MAP.get(v.lower(), v.lower())

    model_config = {
        "populate_by_name": True  # 允许通过 provider 或 model_provider 来赋值
    }

class ValidMCP(BaseModel):
    id: int
    user_id: Optional[int]
    mcp_name: str
    transport: str
    config_json: Optional[dict]
    has_mcp: bool


class ValidApiTool(BaseModel):
    id: int
    name: str
    description: Optional[str]
    url: str
    method: str
    headers: Optional[dict]
    param_location: str
    fixed_params: Optional[dict]
    tool_params: Optional[List[Any]]
    response_extract: Optional[List[Any]]
    response_max_chars: int


class ValidImageTool(BaseModel):
    id: int
    name: str
    description: Optional[str]
    provider: str
    api_key: str
    base_url: Optional[str]
    model: Optional[str]
    default_size: Optional[str]
    default_quality: Optional[str]
    default_style: Optional[str]
    extra_params: Optional[dict]
    support_img2img: bool = False


class ValidAgent(BaseModel):
    id: int

    user_id: int
    avatar: Optional[str]
    model_id: int
    description: Optional[str]
    system_prompt: Optional[str]
    max_token_size: Optional[int]
    human_in_the_loop: bool
    llm: Optional[ValidChatModel] = None
    mcps: Optional[List[ValidMCP]] = None
    api_tools: Optional[List[ValidApiTool]] = None
    image_tools: Optional[List[ValidImageTool]] = None
    builtin_tools: Optional[List[str]] = None

    @field_validator("mcps")
    @classmethod
    def filter_invalid_mcps(cls, v):
        if v is None:
            return v
        return [mcp for mcp in v if mcp.has_mcp]

    model_config = {
        "from_attributes": True
    }

