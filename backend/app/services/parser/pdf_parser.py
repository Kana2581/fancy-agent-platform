import asyncio
import io

from app.services.parser.base import BaseFileParser


class PDFParser(BaseFileParser):

    async def parse(self, data: bytes) -> str:
        return await asyncio.to_thread(self._extract_text, data)

    @staticmethod
    def _extract_text(data: bytes) -> str:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)
