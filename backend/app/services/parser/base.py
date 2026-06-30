# app/services/parser/base.py
from abc import ABC, abstractmethod


class BaseFileParser(ABC):

    @abstractmethod
    async def parse(self, data: bytes) -> str:
        """Return plain text extracted from the file bytes."""
        pass
