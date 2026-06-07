from app.mappers.base_mapper import BaseMapper
from app.models.prompt_template import PromptTemplate


class PromptTemplateMapper(BaseMapper):
    model = PromptTemplate
