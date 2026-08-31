from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


FieldType = Literal[
    "string",
    "number",
    "integer",
    "boolean",
    "date",
    "enum",
    "object_array",
]


class StructuredOutputField(BaseModel):
    key: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    label: str = Field(min_length=1, max_length=100)
    type: FieldType
    description: str | None = Field(default=None, max_length=500)
    enum_values: list[str] | None = Field(default=None, max_length=50)
    item_fields: list["StructuredOutputField"] | None = Field(default=None, max_length=30)

    @field_validator("key", "label", mode="before")
    @classmethod
    def strip_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("description", mode="before")
    @classmethod
    def strip_optional_text(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def validate_enum_values(self):
        if self.type != "enum":
            self.enum_values = None
        else:
            values = [value.strip() for value in (self.enum_values or []) if value.strip()]
            if not values:
                raise ValueError("enum 字段至少需要一个枚举值")
            if any(len(value) > 100 for value in values):
                raise ValueError("枚举值长度不能超过 100")
            if len(values) != len(set(values)):
                raise ValueError("枚举值不能重复")
            self.enum_values = values
        if self.type != "object_array":
            self.item_fields = None
            return self
        item_fields = self.item_fields or []
        if not item_fields:
            raise ValueError("对象列表字段至少需要一个子字段")
        if any(field.type == "object_array" for field in item_fields):
            raise ValueError("对象列表暂不支持嵌套对象列表")
        keys = [field.key for field in item_fields]
        if len(keys) != len(set(keys)):
            raise ValueError("对象列表子字段 key 不能重复")
        self.item_fields = item_fields
        return self


class StructuredOutputFieldConfig(BaseModel):
    fields: list[StructuredOutputField] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_unique_keys(self):
        keys = [field.key for field in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("字段 key 不能重复")
        return self


class StructuredOutputSchemaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    field_config: StructuredOutputFieldConfig

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class StructuredOutputSchemaUpdate(StructuredOutputSchemaCreate):
    pass


class StructuredOutputSchemaOut(StructuredOutputSchemaCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
