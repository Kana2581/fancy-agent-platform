from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.structured_output_schema_mapper import StructuredOutputSchemaMapper
from app.models.structured_output_schema import StructuredOutputSchema
from app.schemas.structured_output_schema import (
    StructuredOutputSchemaCreate,
    StructuredOutputSchemaUpdate,
)
from app.utils.structured_output import compile_json_schema


class StructuredOutputSchemaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = StructuredOutputSchemaMapper(db)

    async def create(self, user_id: int, data: StructuredOutputSchemaCreate) -> StructuredOutputSchema:
        payload = data.model_dump(mode="json")
        compile_json_schema(payload["field_config"], name=payload["name"], description=payload["description"])
        result = await self.mapper.create_from_dict({"user_id": user_id, **payload})
        await self.db.commit()
        return result

    async def list_by_user(self, user_id: int) -> list[StructuredOutputSchema]:
        return await self.mapper.list_by_filters({"user_id": user_id}, limit=100)

    async def get_for_user(self, schema_id: int, user_id: int) -> StructuredOutputSchema | None:
        result = await self.mapper.get_by_id(schema_id)
        return result if result and result.user_id == user_id else None

    async def update(
        self,
        schema: StructuredOutputSchema,
        data: StructuredOutputSchemaUpdate,
    ) -> StructuredOutputSchema:
        payload = data.model_dump(mode="json")
        compile_json_schema(payload["field_config"], name=payload["name"], description=payload["description"])
        result = await self.mapper.update_by_id(schema.id, payload)
        await self.db.commit()
        return result

    async def delete(self, schema: StructuredOutputSchema) -> None:
        await self.mapper.delete_by_id(schema.id)
        await self.db.commit()
