import os
import uuid
from datetime import date
from pathlib import Path
from typing import Set

import aiofiles
from fastapi import UploadFile, HTTPException

from app.services.storage.base import BaseFileUploader


class LocalFileUploader(BaseFileUploader):
    """
    本地磁盘存储，配合 Nginx 对外提供访问
    """

    def __init__(
        self,
        upload_dir: str = "/data/uploads",
        base_url: str = "http://localhost/files",
        allowed_types: Set[str] = None,
        allowed_extensions: Set[str] = None,
        max_size_mb: int = 10,
    ):
        self.upload_dir = Path(upload_dir)
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

        # 新增：扩展名白名单
        self.allowed_extensions = allowed_extensions or {
            ".jpg", ".jpeg", ".png", ".gif", ".webp",
            ".pdf",
            ".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".toml",
            ".xml", ".html", ".htm", ".css", ".sql", ".sh", ".bash", ".zsh",
            ".log", ".ini", ".conf", ".env",
            ".docx",
            # 代码文件
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".c", ".cpp", ".cc", ".h", ".hpp",
            ".cs", ".go", ".rs", ".rb", ".php",
            ".swift", ".kt", ".scala", ".r", ".m",
            ".vue", ".svelte", ".lua", ".pl",
            ".ex", ".exs", ".dart", ".tf",
        }

        self.max_size = max_size_mb * 1024 * 1024

        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def validate(self, file: UploadFile) -> None:
        """
        优化后的文件验证：
        - 校验扩展名（扩展名在白名单即放行，MIME 对代码文件不可靠）
        - 扩展名不在白名单时再校验 MIME（兜底）
        - 流式校验大小
        """

        # 1️⃣ 校验扩展名
        ext = Path(file.filename).suffix.lower()
        if ext not in self.allowed_extensions:
            # 扩展名不在白名单，再看 MIME 是否允许（兜底）
            if file.content_type not in self.allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件类型: {ext} ({file.content_type})",
                )

        # 3️⃣ 流式校验文件大小（避免一次性读入内存）
        size = 0
        chunk_size = 1024 * 1024  # 1MB

        while chunk := await file.read(chunk_size):
            size += len(chunk)
            if size > self.max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件大小超过限制 {self.max_size // 1024 // 1024}MB",
                )

        await file.seek(0)

    async def save(self, file: UploadFile, filename: str = None) -> str:
        """
        保存文件：
        - 自动生成安全文件名
        - 按日期分目录
        """

        date_dir = date.today().strftime("%Y/%m/%d")
        save_dir = self.upload_dir / date_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        # 防止路径穿越
        ext = Path(file.filename).suffix.lower()
        safe_name = filename or f"{uuid.uuid4().hex}{ext}"

        file_path = save_dir / safe_name

        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)

        return f"{date_dir}/{safe_name}"

    async def save_bytes(self, data: bytes, ext: str) -> str:
        """
        直接保存原始字节（用于非 UploadFile 来源，如邮件附件）：
        - 按日期分目录
        - 自动生成安全文件名
        """
        date_dir = date.today().strftime("%Y/%m/%d")
        save_dir = self.upload_dir / date_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        ext = ext.lower()
        if not ext.startswith("."):
            ext = "." + ext
        safe_name = f"{uuid.uuid4().hex}{ext}"

        file_path = save_dir / safe_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)

        return f"{date_dir}/{safe_name}"

    async def save_raw_bytes(self, data: bytes, key: str) -> None:
        path = self.upload_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)

    async def get_url(self, key: str) -> str:
        return f"{self.base_url}/{key}"

    async def delete(self, key: str) -> None:
        file_path = self.upload_dir / key

        # 防止删除越界
        if not file_path.resolve().is_relative_to(self.upload_dir.resolve()):
            raise HTTPException(status_code=400, detail="非法路径")

        if file_path.exists():
            file_path.unlink()
        else:
            raise FileNotFoundError(f"文件不存在: {key}")

    @property
    def storage_type(self) -> str:
        return "local"