from app.services.parser.base import BaseFileParser


class TextParser(BaseFileParser):

    async def parse(self, data: bytes) -> str:
        return data.decode("utf-8", errors="ignore")
