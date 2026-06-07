from app.mappers.base_mapper import BaseMapper
from app.models.llm import LLM


class LLMMapper(BaseMapper):
    model=LLM
