from copy import deepcopy
from typing import Any

from jsonschema import Draft202012Validator

from app.schemas.structured_output_schema import StructuredOutputFieldConfig


_TYPE_SCHEMAS: dict[str, dict[str, Any]] = {
    "string": {"type": "string"},
    "number": {"type": "number"},
    "integer": {"type": "integer"},
    "boolean": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
}


def validate_field_config(field_config: dict[str, Any]) -> StructuredOutputFieldConfig:
    return StructuredOutputFieldConfig.model_validate(field_config)


def _compile_scalar_value_schema(field) -> dict[str, Any]:
    return (
        {"type": "string", "enum": field.enum_values}
        if field.type == "enum"
        else deepcopy(_TYPE_SCHEMAS[field.type])
    )


def _compile_field_value_schema(field) -> dict[str, Any]:
    if field.type != "object_array":
        return _compile_scalar_value_schema(field)

    item_properties: dict[str, Any] = {}
    item_fields = field.item_fields or []
    for item_field in item_fields:
        item_value_schema = _compile_scalar_value_schema(item_field)
        item_properties[item_field.key] = {
            "title": item_field.label,
            "description": item_field.description
            or f"{item_field.label}；无法确认时返回 null",
            "anyOf": [item_value_schema, {"type": "null"}],
        }

    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": item_properties,
            "required": [item_field.key for item_field in item_fields],
            "additionalProperties": False,
        },
    }


def compile_json_schema(
    field_config: dict[str, Any],
    *,
    name: str,
    description: str | None = None,
) -> dict[str, Any]:
    config = validate_field_config(field_config)
    properties: dict[str, Any] = {}

    for field in config.fields:
        value_schema = _compile_field_value_schema(field)
        properties[field.key] = {
            "title": field.label,
            "description": field.description or f"{field.label}；无法确认时返回 null",
            "anyOf": [value_schema, {"type": "null"}],
        }

    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "structured_output",
        "description": description or f"{name} 的完整结构化结果。所有字段必须返回，无法确认时返回 null。",
        "type": "object",
        "properties": properties,
        "required": [field.key for field in config.fields],
        "additionalProperties": False,
    }
    Draft202012Validator.check_schema(schema)
    return schema
