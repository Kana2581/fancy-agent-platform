from app.services.parser.base import BaseFileParser

from pathlib import Path
class TextParser(BaseFileParser):

    async def parse(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8", errors="ignore")