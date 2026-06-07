import asyncio
from pathlib import Path

from app.services.parser.base import BaseFileParser


class DocxParser(BaseFileParser):

    async def parse(self, file_path: Path) -> str:
        return await asyncio.to_thread(self._extract_text, file_path)

    @staticmethod
    def _extract_text(file_path: Path) -> str:
        from docx import Document

        doc = Document(str(file_path))
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        # 提取表格内容
        for table in doc.tables:
            for row in table.rows:
                row_text = "\t".join(cell.text.strip() for cell in row.cells)
                if row_text.strip():
                    parts.append(row_text)
        return "\n".join(parts)
