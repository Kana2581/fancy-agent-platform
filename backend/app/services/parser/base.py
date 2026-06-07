# app/services/parser/base.py
from abc import ABC, abstractmethod
from pathlib import Path


class BaseFileParser(ABC):

    @abstractmethod
    async def parse(self, file_path: Path) -> str:
        """返回纯文本内容"""
        pass