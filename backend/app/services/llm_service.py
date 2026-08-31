# app/services/llm_service.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from langchain.chat_models import init_chat_model

from app.mappers.llm_mapper import LLMMapper
from app.schemas.llm_schema import LLMCreate, LLMUpdate, LLMTestRequest
from app.schemas.dto.langchian import ValidChatModel
from app.models.llm import LLM
from app.utils.langchain.api_mode import model_init_kwargs


class LLMService:

    def __init__(self,db: AsyncSession):
        self.db = db
        self.mapper = LLMMapper(db)

    async def create_llm(self, data: dict) -> LLM:
        self._validate_api_mode(data.get("provider"), data.get("api_mode", "chat_completions"))
        res = await self.mapper.create_from_dict(data)
        await self.db.commit()
        return res

    async def update_llm(self, llm_id: int, data: LLMUpdate) -> Optional[LLM]:
        existing = await self.mapper.get_by_id(llm_id)
        update_data = data.model_dump(exclude_unset=True)
        self._validate_api_mode(
            update_data.get("provider", existing.provider if existing else None),
            update_data.get("api_mode", existing.api_mode if existing else "chat_completions"),
        )
        res = await self.mapper.update_by_id(
            llm_id,
            update_data
        )
        await self.db.commit()
        return res

    async def delete_llm(self, llm_id: int) -> bool:
        res = await self.mapper.delete_by_id(llm_id)
        await self.db.commit()
        return res

    async def get_llm(self, llm_id: int) -> Optional[LLM]:
        return await self.mapper.get_by_id(llm_id)

    async def test_llm(self, data: LLMTestRequest, user_id: int) -> tuple[bool, str]:
        api_key = data.api_key
        if not api_key and data.llm_id is not None:
            existing = await self.mapper.get_by_id(data.llm_id)
            if existing and existing.user_id == user_id:
                api_key = existing.api_key

        if not api_key:
            return False, "API Key 不能为空"

        try:
            self._validate_api_mode(data.provider, data.api_mode)
        except ValueError as exc:
            return False, str(exc)

        try:
            model_config = ValidChatModel.model_validate({
                "provider": data.provider,
                "model_name": data.model_name,
                "base_url": data.base_url,
                "api_key": api_key,
                "api_mode": data.api_mode,
            })
            model = init_chat_model(**model_init_kwargs(model_config))
            resp = await model.ainvoke("hi")
            content = getattr(resp, "content", "") or ""
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            preview = content.strip()[:120] or "(空响应)"
            return True, f"连接成功，模型回复：{preview}"
        except Exception as e:
            return False, f"连接失败：{e}"

    async def list_llms_by_user(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 100,
    ) -> List[LLM]:
        return await self.mapper.list_by_filters(
            filters={"user_id": user_id},
            offset=offset,
            limit=limit,
        )

    @staticmethod
    def _validate_api_mode(provider: Optional[str], api_mode: Optional[str]) -> None:
        """Responses is an OpenAI/OpenAI-compatible protocol only."""
        if api_mode != "responses":
            return
        normalized = (provider or "").strip().lower()
        # These entries all resolve to LangChain's OpenAI-compatible adapter.
        if normalized not in {"openai", "custom", "aliyun"}:
            raise ValueError("Responses API 仅支持 OpenAI 或 OpenAI-compatible 配置")
