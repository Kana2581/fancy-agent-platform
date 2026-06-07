import json
import unicodedata
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import settings

_UNICODE_QUOTE_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u201e": '"', "\u201f": '"',
    "\u2013": "-", "\u2014": "-", "\u2015": "-",
    "\u2026": "...",
    "\u00a0": " ", "\u202f": " ", "\u3000": " ",
})


def _normalize_query(query: str) -> str:
    """Replace fancy Unicode punctuation that latin-1 cannot encode."""
    query = unicodedata.normalize("NFKC", query).translate(_UNICODE_QUOTE_MAP)
    # 兜底：将剩余 latin-1 无法编码的标点/符号替换为空格，保留中文等文字字符
    result = []
    for ch in query:
        try:
            ch.encode("latin-1")
            result.append(ch)
        except UnicodeEncodeError:
            category = unicodedata.category(ch)
            result.append(" " if category.startswith(("P", "S")) else ch)
    return " ".join("".join(result).split())  # 顺手合并多余空格

class WebSearchInput(BaseModel):
    query: str = Field(description="要搜索的查询词")
    max_results: Optional[int] = Field(default=None, description="返回结果数量上限")


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "搜索互联网获取实时信息。输入查询词，返回相关网页摘要列表。"
        "适合查询最新新闻、事实信息、当前事件等。"
    )
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str, max_results: Optional[int] = None) -> str:
        query = _normalize_query(query)
        max_results = max_results or settings.WEB_SEARCH_MAX_RESULTS
        try:
            if settings.SEARCH_PROVIDER == "tavily" and settings.TAVILY_API_KEY:
                return self._search_tavily(query, max_results)
            else:
                return self._search_duckduckgo(query, max_results)
        except Exception as e:
            return json.dumps({"error": f"搜索失败: {str(e)}"}, ensure_ascii=False)

    def _search_tavily(self, query: str, max_results: int) -> str:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(query, max_results=max_results)
        results = []
        for r in response.get("results", []):
            snippet = (r.get("content") or "")[:500]
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": snippet,
            })
        return json.dumps(results, ensure_ascii=False)

    def _search_duckduckgo(self, query: str, max_results: int) -> str:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                snippet = (r.get("body") or "")[:500]
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": snippet,
                })
        return json.dumps(results, ensure_ascii=False)

    async def _arun(self, query: str, max_results: Optional[int] = None) -> str:
        query = _normalize_query(query)
        max_results = max_results or settings.WEB_SEARCH_MAX_RESULTS
        try:
            if settings.SEARCH_PROVIDER == "tavily" and settings.TAVILY_API_KEY:
                return await self._asearch_tavily(query, max_results)
            else:
                return await self._asearch_duckduckgo(query, max_results)
        except Exception as e:
            return json.dumps({"error": f"搜索失败: {str(e)}"}, ensure_ascii=False)

    async def _asearch_tavily(self, query: str, max_results: int) -> str:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
        response = await client.search(query, max_results=max_results)
        results = []
        for r in response.get("results", []):
            snippet = (r.get("content") or "")[:500]
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": snippet,
            })
        return json.dumps(results, ensure_ascii=False)

    async def _asearch_duckduckgo(self, query: str, max_results: int) -> str:
        from ddgs import AsyncDDGS
        results = []
        async with AsyncDDGS() as ddgs:
            async for r in ddgs.text(query, max_results=max_results):
                snippet = (r.get("body") or "")[:500]
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": snippet,
                })
        return json.dumps(results, ensure_ascii=False)


def build_web_search_tool() -> BaseTool:
    return WebSearchTool()
