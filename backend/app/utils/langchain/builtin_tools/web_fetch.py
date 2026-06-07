import json
from typing import Type

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import settings


class WebFetchInput(BaseModel):
    url: str = Field(description="要抓取的网页 URL")


class WebFetchTool(BaseTool):
    name: str = "web_fetch"
    description: str = (
        "抓取指定 URL 的网页正文内容。返回标题和正文文本，自动去除导航栏、广告等噪音。"
        "适合阅读文章、文档、博客等网页内容。"
    )
    args_schema: Type[BaseModel] = WebFetchInput

    def _run(self, url: str) -> str:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # 移除噪音标签
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else ""

            # 正文优先级：article > main > body
            content_tag = soup.find("article") or soup.find("main") or soup.find("body")
            raw_text = content_tag.get_text(separator="\n", strip=True) if content_tag else ""

            # 合并多余空行
            lines = [line for line in raw_text.splitlines() if line.strip()]
            content = "\n".join(lines)

            max_chars = settings.WEB_FETCH_MAX_CHARS
            truncated = len(content) > max_chars
            if truncated:
                content = content[:max_chars]

            return json.dumps(
                {
                    "url": url,
                    "title": title,
                    "content": content,
                    "total_chars": len(content),
                    "truncated": truncated,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps({"error": f"抓取失败: {str(e)}", "url": url}, ensure_ascii=False)

    async def _arun(self, url: str) -> str:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else ""

            content_tag = soup.find("article") or soup.find("main") or soup.find("body")
            raw_text = content_tag.get_text(separator="\n", strip=True) if content_tag else ""

            lines = [line for line in raw_text.splitlines() if line.strip()]
            content = "\n".join(lines)

            max_chars = settings.WEB_FETCH_MAX_CHARS
            truncated = len(content) > max_chars
            if truncated:
                content = content[:max_chars]

            return json.dumps(
                {
                    "url": url,
                    "title": title,
                    "content": content,
                    "total_chars": len(content),
                    "truncated": truncated,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps({"error": f"抓取失败: {str(e)}", "url": url}, ensure_ascii=False)


def build_web_fetch_tool() -> BaseTool:
    return WebFetchTool()

