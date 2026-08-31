from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db
from app.deps.user import get_current_user
from app.schemas.structured_output_schema import (
    StructuredOutputSchemaCreate,
    StructuredOutputSchemaOut,
    StructuredOutputSchemaUpdate,
)
from app.services.structured_output_schema_service import StructuredOutputSchemaService


router = APIRouter(prefix="/structured-output-schemas", tags=["Structured Output Schemas"])


def get_service(db: AsyncSession = Depends(get_db)) -> StructuredOutputSchemaService:
    return StructuredOutputSchemaService(db)


@router.post("", response_model=StructuredOutputSchemaOut)
async def create_schema(
    data: StructuredOutputSchemaCreate,
    user_id: int = Depends(get_current_user),
    service: StructuredOutputSchemaService = Depends(get_service),
):
    return await service.create(user_id, data)


@router.get("", response_model=list[StructuredOutputSchemaOut])
async def list_schemas(
    user_id: int = Depends(get_current_user),
    service: StructuredOutputSchemaService = Depends(get_service),
):
    return await service.list_by_user(user_id)


async def _owned_schema(schema_id: int, user_id: int, service: StructuredOutputSchemaService):
    schema = await service.get_for_user(schema_id, user_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Structured output schema not found")
    return schema


@router.get("/{schema_id}", response_model=StructuredOutputSchemaOut)
async def get_schema(
    schema_id: int,
    user_id: int = Depends(get_current_user),
    service: StructuredOutputSchemaService = Depends(get_service),
):
    return await _owned_schema(schema_id, user_id, service)


@router.put("/{schema_id}", response_model=StructuredOutputSchemaOut)
async def update_schema(
    schema_id: int,
    data: StructuredOutputSchemaUpdate,
    user_id: int = Depends(get_current_user),
    service: StructuredOutputSchemaService = Depends(get_service),
):
    schema = await _owned_schema(schema_id, user_id, service)
    return await service.update(schema, data)


@router.delete("/{schema_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schema(
    schema_id: int,
    user_id: int = Depends(get_current_user),
    service: StructuredOutputSchemaService = Depends(get_service),
):
    schema = await _owned_schema(schema_id, user_id, service)
    await service.delete(schema)
