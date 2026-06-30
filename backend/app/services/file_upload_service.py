from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.chat_file_mapper import ChatFileMapper
from app.models.chat_file import ChatFile
from app.models.chat_file_content import ChatFileContent
from app.schemas.chat_file_schema import ChatFileUploadRequest, ChatFileResponse
from app.services.storage import get_file_uploader
from app.services.parser.factory import FileParserFactory


class FileUploadService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = ChatFileMapper(db)
        self.uploader = get_file_uploader()

    async def upload(
        self,
        file: UploadFile,
        user_id: int,
        req: ChatFileUploadRequest,
    ) -> ChatFileResponse:

        # ① 校验
        await self.uploader.validate(file)
        await file.seek(0)

        # ② 读取原始字节（大小计算 + 解析，与存储后端无关）
        raw = await file.read()
        file_size = len(raw)
        file_ext = Path(file.filename).suffix.lower()
        await file.seek(0)

        # ③ 保存到存储后端
        object_key = await self.uploader.save(file)

        chat_file = await self.mapper.create_from_dict({
            "file_name": file.filename,
            "file_ext": file_ext,
            "file_size": file_size,
            "content_type": file.content_type,
            "storage_type": self.uploader.storage_type,
            "object_key": object_key,
            "md5": None,
            "upload_user_id": user_id,
            "session_id": req.session_id,
            "parse_status": 0,
        })

        await self.db.commit()

        # ④ 使用工厂解析
        parser = FileParserFactory.get_parser(file_ext)

        if parser:
            try:
                content = await parser.parse(raw)

                self.db.add(ChatFileContent(
                    file_id=chat_file.id,
                    content=content,
                    content_length=len(content),
                ))

                chat_file.parse_status = 1

            except Exception:
                chat_file.parse_status = 2

            await self.db.commit()
        else:
            chat_file.parse_status = 1  # images: no text parsing needed, not an error
            await self.db.commit()

        url = await self.uploader.get_url(object_key)
        return self._to_response(chat_file, url)

    async def delete(self, file_id: int, user_id: int) -> None:
        chat_file = await self.mapper.get_by_id(file_id)
        if not chat_file:
            raise HTTPException(status_code=404, detail="文件不存在")
        if chat_file.upload_user_id != user_id:
            raise HTTPException(status_code=403, detail="无权限删除")

        await self.uploader.delete(chat_file.object_key)
        await self.mapper.delete_by_id(file_id)
        await self.db.commit()

    def _to_response(self, chat_file: ChatFile, url: str = "") -> ChatFileResponse:
        return ChatFileResponse(
            id=chat_file.id,
            file_name=chat_file.file_name,
            file_ext=chat_file.file_ext,
            file_size=chat_file.file_size,
            content_type=chat_file.content_type,
            storage_type=chat_file.storage_type,
            url=url or chat_file.object_key,
            md5=chat_file.md5,
            parse_status=chat_file.parse_status,
            created_at=chat_file.created_at,
        )