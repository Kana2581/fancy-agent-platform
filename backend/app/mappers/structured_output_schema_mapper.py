from app.mappers.base_mapper import BaseMapper
from app.models.structured_output_schema import StructuredOutputSchema


class StructuredOutputSchemaMapper(BaseMapper[StructuredOutputSchema]):
    model = StructuredOutputSchema
