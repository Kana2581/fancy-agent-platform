# app/services/storage/base.py
import hashlib
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod
from fastapi import UploadFile


@dataclass
class UploadResult:
    object_key: str
    url: str
    storage_type: str          # "local" / "minio"
    original_filename: str
    file_ext: str
    file_size: int
    content_type: Optional[str]
    md5: str


class BaseFileUploader(ABC):

    async def before_upload(self, file: UploadFile) -> None: pass
    async def after_upload(self, file: UploadFile, result: UploadResult) -> None: pass

    @abstractmethod
    async def validate(self, file: UploadFile) -> None: ...

    @abstractmethod
    async def save(self, file: UploadFile, filename: str) -> str:
        """返回 object_key"""
        ...

    async def generate_filename(self, file: UploadFile) -> str:
        import uuid, os
        ext = os.path.splitext(file.filename or "")[-1]
        return f"{uuid.uuid4().hex}{ext}"

    async def get_url(self, key: str) -> str:
        return key

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def upload(self, file: UploadFile) -> UploadResult:
        import os
        await self.before_upload(file)

        # 读取全部内容，用于计算大小和 md5
        raw = await file.read()
        file_size = len(raw)
        md5 = hashlib.md5(raw).hexdigest()
        await file.seek(0)

        await self.validate(file)

        filename = await self.generate_filename(file)
        key = await self.save(file, filename)
        url = await self.get_url(key)
        ext = os.path.splitext(file.filename or "")[-1].lstrip(".")

        result = UploadResult(
            object_key=key,
            url=url,
            storage_type=self.storage_type,
            original_filename=file.filename or filename,
            file_ext=ext,
            file_size=file_size,
            content_type=file.content_type,
            md5=md5,
        )
        await self.after_upload(file, result)
        return result

    @property
    @abstractmethod
    def storage_type(self) -> str: ...