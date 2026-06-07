import json
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.deps.db import get_db_session
from app.mappers.prompt_template_mapper import PromptTemplateMapper
from app.schemas.prompt_template_schema import PromptTemplateUpdate
from app.services.prompt_template_service import PromptTemplateService


class ListPromptTemplatesInput(BaseModel):
    category: Optional[str] = Field(default=None, description="按分类过滤，不填则返回全部")


class GetPromptTemplateInput(BaseModel):
    template_id: int = Field(description="要查看的提示词模板 ID")


class CreatePromptTemplateInput(BaseModel):
    name: str = Field(description="模板名称，需唯一")
    content: str = Field(description="提示词内容")
    description: Optional[str] = Field(default=None, description="简短描述")
    category: Optional[str] = Field(default=None, description="分类标签，可选")


class UpdatePromptTemplateInput(BaseModel):
    template_id: int = Field(description="要修改的模板 ID")
    name: Optional[str] = Field(default=None, description="新名称")
    content: Optional[str] = Field(default=None, description="新内容")
    description: Optional[str] = Field(default=None, description="新描述")
    category: Optional[str] = Field(default=None, description="新分类")


class DeletePromptTemplateInput(BaseModel):
    template_id: int = Field(description="要删除的模板 ID")


def build_prompt_template_tools(user_id: int) -> List[BaseTool]:
    class ListPromptTemplatesTool(BaseTool):
        name: str = "list_prompt_templates"
        description: str = "列出当前用户的所有提示词模板，返回 ID、名称、描述和分类（不含完整内容）"
        args_schema: Type[BaseModel] = ListPromptTemplatesInput

        async def _arun(self, category: Optional[str] = None) -> str:
            async with get_db_session() as db:
                templates = await PromptTemplateService(db).list_by_user(user_id, category=category)
                return json.dumps(
                    [
                        {
                            "id": t.id,
                            "name": t.name,
                            "description": t.description or "",
                            "category": t.category or "",
                        }
                        for t in templates
                    ],
                    ensure_ascii=False,
                )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class GetPromptTemplateTool(BaseTool):
        name: str = "get_prompt_template"
        description: str = "获取指定提示词模板的完整内容"
        args_schema: Type[BaseModel] = GetPromptTemplateInput

        async def _arun(self, template_id: int) -> str:
            async with get_db_session() as db:
                template = await PromptTemplateService(db).get_prompt_template(template_id)
                if not template or template.user_id != user_id:
                    return f"未找到 ID 为 {template_id} 的提示词模板"
                return json.dumps(
                    {
                        "id": template.id,
                        "name": template.name,
                        "content": template.content,
                        "description": template.description or "",
                        "category": template.category or "",
                    },
                    ensure_ascii=False,
                )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class CreatePromptTemplateTool(BaseTool):
        name: str = "create_prompt_template"
        description: str = "创建并保存一个新的提示词模板"
        args_schema: Type[BaseModel] = CreatePromptTemplateInput

        async def _arun(
            self,
            name: str,
            content: str,
            description: Optional[str] = None,
            category: Optional[str] = None,
        ) -> str:
            async with get_db_session() as db:
                template = await PromptTemplateService(db).create_prompt_template(
                    {
                        "user_id": user_id,
                        "name": name,
                        "content": content,
                        "description": description,
                        "category": category,
                    }
                )
                return json.dumps({"id": template.id, "name": template.name}, ensure_ascii=False)

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class UpdatePromptTemplateTool(BaseTool):
        name: str = "update_prompt_template"
        description: str = "修改已有提示词模板的名称、内容、描述或分类"
        args_schema: Type[BaseModel] = UpdatePromptTemplateInput

        async def _arun(
            self,
            template_id: int,
            name: Optional[str] = None,
            content: Optional[str] = None,
            description: Optional[str] = None,
            category: Optional[str] = None,
        ) -> str:
            async with get_db_session() as db:
                template = await PromptTemplateMapper(db).get_by_id(template_id)
                if not template or template.user_id != user_id:
                    return json.dumps({"error": f"未找到 ID 为 {template_id} 的提示词模板"}, ensure_ascii=False)
                updated = await PromptTemplateService(db).update_prompt_template(
                    template_id,
                    PromptTemplateUpdate(name=name, content=content, description=description, category=category),
                )
                if not updated:
                    return json.dumps({"error": "更新失败"}, ensure_ascii=False)
                return json.dumps({"id": updated.id, "name": updated.name}, ensure_ascii=False)

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class DeletePromptTemplateTool(BaseTool):
        name: str = "delete_prompt_template"
        description: str = "删除指定的提示词模板"
        args_schema: Type[BaseModel] = DeletePromptTemplateInput

        async def _arun(self, template_id: int) -> str:
            async with get_db_session() as db:
                template = await PromptTemplateMapper(db).get_by_id(template_id)
                if not template or template.user_id != user_id:
                    return json.dumps({"error": f"未找到 ID 为 {template_id} 的提示词模板"}, ensure_ascii=False)
                await PromptTemplateService(db).delete_prompt_template(template_id)
                return json.dumps({"success": True, "id": template_id}, ensure_ascii=False)

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    return [
        ListPromptTemplatesTool(),
        GetPromptTemplateTool(),
        CreatePromptTemplateTool(),
        UpdatePromptTemplateTool(),
        DeletePromptTemplateTool(),
    ]
