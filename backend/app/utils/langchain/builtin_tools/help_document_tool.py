import json
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.deps.db import get_db_session
from app.services.help_document_service import HelpDocumentService


class ListHelpDocumentsInput(BaseModel):
    q: Optional[str] = Field(default=None, description="搜索关键词，可匹配标题、摘要和正文")
    category: Optional[str] = Field(default=None, description="分类过滤，如：Agent 组成、配置区、知识增强")
    doc_type: Optional[str] = Field(default=None, description="文档类型过滤，如：overview、agent_component、knowledge_feature、page")


class GetHelpDocumentInput(BaseModel):
    slug: str = Field(description="文档 slug。若不确定，请先调用 list_help_documents")


def build_help_document_tools() -> List[BaseTool]:
    class ListHelpDocumentsTool(BaseTool):
        name: str = "list_help_documents"
        description: str = (
            "列出或搜索 Fancy Agent 平台帮助文档，返回文档 slug、标题、摘要、分类和页面路由。"
            "回答平台功能、配置方式、工具用途等问题前，应先用此工具查找相关文档。"
        )
        args_schema: Type[BaseModel] = ListHelpDocumentsInput

        async def _arun(
            self,
            q: Optional[str] = None,
            category: Optional[str] = None,
            doc_type: Optional[str] = None,
        ) -> str:
            async with get_db_session() as db:
                docs = await HelpDocumentService(db).list_documents(
                    q=q,
                    category=category,
                    doc_type=doc_type,
                    limit=50,
                )
                return json.dumps(
                    [
                        {
                            "slug": d.slug,
                            "title": d.title,
                            "summary": d.summary,
                            "category": d.category or "",
                            "doc_type": d.doc_type,
                            "route": d.route or "",
                        }
                        for d in docs
                    ],
                    ensure_ascii=False,
                )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class GetHelpDocumentTool(BaseTool):
        name: str = "get_help_document"
        description: str = "按 slug 获取 Fancy Agent 帮助文档完整内容。"
        args_schema: Type[BaseModel] = GetHelpDocumentInput

        async def _arun(self, slug: str) -> str:
            async with get_db_session() as db:
                doc = await HelpDocumentService(db).get_by_slug(slug)
                if not doc:
                    return f"未找到 slug 为「{slug}」的帮助文档，请先调用 list_help_documents。"
                return json.dumps(
                    {
                        "slug": doc.slug,
                        "title": doc.title,
                        "summary": doc.summary,
                        "category": doc.category or "",
                        "doc_type": doc.doc_type,
                        "route": doc.route or "",
                        "content": doc.content,
                    },
                    ensure_ascii=False,
                )

        def _run(self, slug: str) -> str:
            raise NotImplementedError("Use async version")

    return [ListHelpDocumentsTool(), GetHelpDocumentTool()]
