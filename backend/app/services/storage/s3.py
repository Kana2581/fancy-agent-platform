import uuid
from datetime import date
from pathlib import Path
from typing import Optional, Set

import aioboto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException

from app.services.storage.base import BaseFileUploader


class S3FileUploader(BaseFileUploader):
    """S3-compatible storage backend (Alibaba Cloud OSS / AWS S3 / MinIO).

    All I/O is natively async via aioboto3.
    """

    def __init__(
        self,
        session: aioboto3.Session,
        bucket: str,
        base_url: str,
        endpoint_url: Optional[str] = None,
        allowed_types: Optional[Set[str]] = None,
        allowed_extensions: Optional[Set[str]] = None,
        max_size_mb: int = 10,
    ):
        self._session = session
        self._bucket = bucket
        self._endpoint_url = endpoint_url or None
        self.base_url = base_url.rstrip("/")

        self.allowed_types = allowed_types or {
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "application/pdf",
            "text/plain",
            "text/markdown",
            "application/json",
            "text/csv",
            "application/octet-stream",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }

        self.allowed_extensions = allowed_extensions or {
            ".jpg", ".jpeg", ".png", ".gif", ".webp",
            ".pdf",
            ".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".toml",
            ".xml", ".html", ".htm", ".css", ".sql", ".sh", ".bash", ".zsh",
            ".log", ".ini", ".conf", ".env",
            ".docx",
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".c", ".cpp", ".cc", ".h", ".hpp",
            ".cs", ".go", ".rs", ".rb", ".php",
            ".swift", ".kt", ".scala", ".r", ".m",
            ".vue", ".svelte", ".lua", ".pl",
            ".ex", ".exs", ".dart", ".tf",
        }

        self.max_size = max_size_mb * 1024 * 1024

    def _client(self):
        # OSS S3 兼容层要求：
        # - virtual-hosted 寻址（bucket.endpoint），新版 botocore 默认 path-style 会被拒
        # - 关闭 botocore 1.36+ 新增的 CRC32 校验和，OSS 不支持 aws-chunked 编码
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    async def validate(self, file: UploadFile) -> None:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in self.allowed_extensions:
            if file.content_type not in self.allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件类型: {ext} ({file.content_type})",
                )

        size = 0
        chunk_size = 1024 * 1024
        while chunk := await file.read(chunk_size):
            size += len(chunk)
            if size > self.max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件大小超过限制 {self.max_size // 1024 // 1024}MB",
                )
        await file.seek(0)

    async def save(self, file: UploadFile, filename: Optional[str] = None) -> str:
        date_dir = date.today().strftime("%Y/%m/%d")
        ext = Path(file.filename or "").suffix.lower()
        safe_name = filename or f"{uuid.uuid4().hex}{ext}"
        key = f"{date_dir}/{safe_name}"
        data = await file.read()
        async with self._client() as s3:
            await s3.put_object(Bucket=self._bucket, Key=key, Body=data)
        return key

    async def save_bytes(self, data: bytes, ext: str) -> str:
        date_dir = date.today().strftime("%Y/%m/%d")
        ext = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        key = f"{date_dir}/{uuid.uuid4().hex}{ext}"
        async with self._client() as s3:
            await s3.put_object(Bucket=self._bucket, Key=key, Body=data)
        return key

    async def save_raw_bytes(self, data: bytes, key: str) -> None:
        async with self._client() as s3:
            await s3.put_object(Bucket=self._bucket, Key=key, Body=data)

    async def get_url(self, key: str) -> str:
        from app.services.storage.url_signer import build_storage_url

        return build_storage_url(key)

    async def delete(self, key: str) -> None:
        async with self._client() as s3:
            try:
                await s3.delete_object(Bucket=self._bucket, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                    raise FileNotFoundError(f"S3 object not found: {key}")
                raise

    @property
    def storage_type(self) -> str:
        return "s3"
