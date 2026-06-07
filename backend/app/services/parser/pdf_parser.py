import asyncio
from pathlib import Path

from app.services.parser.base import BaseFileParser


class PDFParser(BaseFileParser):

    async def parse(self, file_path: Path) -> str:
        return await asyncio.to_thread(self._extract_text, file_path)

    @staticmethod
    def _extract_text(file_path: Path) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)
