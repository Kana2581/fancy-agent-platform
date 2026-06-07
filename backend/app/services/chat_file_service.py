import re
from typing import Callable, List, Optional, Dict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.chat_file_content_mapper import ChatFileContentMapper
from app.mappers.chat_file_mapper import ChatFileMapper
from app.mappers.chat_message_file_mapper import ChatMessageFileMapper
from app.models.chat_file import ChatFile
from app.models.chat_file_content import ChatFileContent
from app.models.chat_message_file import ChatMessageFile
from app.schemas.dto.file_message import ChatFileWithContent
from app.utils.image.local_image_loader import strip_oss_prefix
from app.utils.langchain.image_reference_context import ImageReference, set_image_references
from app.utils.langchain.message_builder import extract_text, build_message_content
from app.utils.langchain.message_builder import IMAGE_EXTENSIONS


# markdown 图片语法：![alt](url "optional title")
_IMAGE_MD_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


ContentItem = dict  # LangChain multimodal content item


class ChatFileService:
    """ChatFile 相关业务逻辑"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._file_mapper = ChatFileMapper(db)
        self._content_mapper = ChatFileContentMapper(db)
        self._msg_file_mapper = ChatMessageFileMapper(db)

    # ------------------------------------------------------------------ #
    #  message <-> file 关联                                               #
    # ------------------------------------------------------------------ #

    async def attach_files_to_message(
        self, message_id: str, file_ids: List[int]
    ) -> List[ChatMessageFile]:
        return await self._msg_file_mapper.bulk_create_for_message(message_id, file_ids)

    async def detach_file_from_message(self, message_id: str, file_id: int) -> bool:
        return await self._msg_file_mapper.delete_by_message_and_file(message_id, file_id)

    async def detach_all_files_from_message(self, message_id: str) -> int:
        return await self._msg_file_mapper.delete_by_message_id(message_id)

    # ------------------------------------------------------------------ #
    #  单消息查询（保留原有接口）                                           #
    # ------------------------------------------------------------------ #

    async def get_files_by_message_id(self, message_id: str) -> List[ChatFile]:
        file_ids = await self._msg_file_mapper.get_file_ids_by_message_id(message_id)
        if not file_ids:
            return []
        files = []
        for fid in file_ids:
            f = await self._file_mapper.get_by_id(fid)
            if f:
                files.append(f)
        return files

    async def get_files_with_content_by_message_id(
        self, message_id: str
    ) -> List[ChatFileWithContent]:
        files = await self.get_files_by_message_id(message_id)
        result: List[ChatFileWithContent] = []
        for f in files:
            content = await self._content_mapper.get_by_file_id(f.id)
            result.append(ChatFileWithContent(file=f, content=content))
        return result

    async def get_file_with_content(self, file_id: int) -> Optional[ChatFileWithContent]:
        f = await self._file_mapper.get_by_id(file_id)
        if f is None:
            return None
        content = await self._content_mapper.get_by_file_id(file_id)
        return ChatFileWithContent(file=f, content=content)

    async def list_files_by_session(self, session_id: str) -> List[ChatFile]:
        return await self._file_mapper.list_by_session(session_id)

    async def list_files_by_user(self, user_id: int) -> List[ChatFile]:
        return await self._file_mapper.list_by_user(user_id)

    # ------------------------------------------------------------------ #
    #  批量注入文件内容到消息列表（核心新功能）                             #
    # ------------------------------------------------------------------ #

    async def inject_files_into_messages(
        self,
        messages: List[BaseMessage],
        user_id: Optional[int] = None,
    ) -> List[BaseMessage]:
        """
        给消息列表批量注入文件内容，返回新列表，原列表不变。

        设计原则：
          - DB 存储的消息 content 保持纯文本，注入只发生在内存中
          - 3 次批量查询搞定全部数据，无 N+1

        图片就地编号：
          - 按时间顺序遍历消息，每遇到一张图片分配一个会话内稳定的 id；
          - 附件图在图片块后追加「图片 #N」文本标记；
          - 生成图改写 AI 消息里的 markdown alt 为「图片 #N」；
          - 引用范围天然限于本会话（messages 即本会话祖先链），不再跨会话拉取。
        """
        # 1. 收集所有带 id 的 HumanMessage id（用于批量拉取附件元数据）
        human_ids: List[str] = [
            m.id
            for m in messages
            if isinstance(m, HumanMessage) and m.id
        ]

        # 2. 批量查 message -> [file_id] -> 元数据/内容（仅当存在附件时；各 1 次 SQL）
        msg_to_file_ids: Dict[str, List[int]] = {}
        file_meta_map: Dict[int, ChatFile] = {}
        content_map: Dict[int, ChatFileContent] = {}
        if human_ids:
            msg_to_file_ids = await self._msg_file_mapper.get_file_ids_by_message_ids(human_ids)
            if msg_to_file_ids:
                all_file_ids: List[int] = list({
                    fid for fids in msg_to_file_ids.values() for fid in fids
                })
                file_meta_map = await self._file_mapper.get_by_ids(all_file_ids)
                content_map = await self._content_mapper.get_by_file_ids(all_file_ids)

        # 3. 就地编号 + 重建消息列表
        image_refs: List[ImageReference] = []
        key_to_ref_id: Dict[str, str] = {}

        def _assign_ref(object_key: str, label: str, source: str) -> str:
            existing = key_to_ref_id.get(object_key)
            if existing:
                return existing
            ref_id = str(len(image_refs) + 1)
            image_refs.append(ImageReference(
                ref_id=ref_id,
                object_key=object_key,
                label=label,
                source=source,
            ))
            key_to_ref_id[object_key] = ref_id
            return ref_id

        result: List[BaseMessage] = []
        for msg in messages:
            # 3a. 带附件的 HumanMessage：注入文件内容，并给图片附件就地编号
            if (
                isinstance(msg, HumanMessage)
                and msg.id
                and msg.id in msg_to_file_ids
            ):
                files_with_content = [
                    ChatFileWithContent(
                        file=file_meta_map[fid],
                        content=content_map.get(fid),
                    )
                    for fid in msg_to_file_ids[msg.id]
                    if fid in file_meta_map
                ]

                for item in files_with_content:
                    file = item.file
                    if file.file_ext.lower() in IMAGE_EXTENSIONS:
                        _assign_ref(file.object_key, file.file_name, "chat_attachment")

                original_text = (
                    msg.content
                    if isinstance(msg.content, str)
                    else extract_text(msg.content)
                )
                new_content = build_message_content(
                    original_text, files_with_content, image_ref_ids=key_to_ref_id
                )
                result.append(msg.model_copy(update={"content": new_content}))
                continue

            # 3b. AI 消息：扫描其中的生成图 markdown，就地编号并改写 alt
            result.append(self._annotate_ai_generated_images(msg, _assign_ref))

        set_image_references(image_refs)
        return result

    @staticmethod
    def _annotate_ai_generated_images(
        msg: BaseMessage,
        assign_ref: Callable[[str, str, str], str],
    ) -> BaseMessage:
        """给 AI 消息里的内部图片 markdown 就地编号。

        只改写指回本站 OSS_URL（可还原为本地 object_key）的图片，外部 URL 原样保留。
        改写仅发生在内存副本，不落库——与「DB 存纯文本、注入只在内存」原则一致。
        """
        if not isinstance(msg, AIMessage):
            return msg
        content = msg.content
        if not isinstance(content, str) or "![" not in content:
            return msg

        changed = False

        def _repl(m: re.Match) -> str:
            nonlocal changed
            alt = m.group(1)
            url = m.group(2).split()[0]  # 去掉可选的 "title"
            object_key = strip_oss_prefix(url)
            if not object_key:
                return m.group(0)
            ref_id = assign_ref(object_key, alt or "generated image", "generated_image")
            changed = True
            return f"![图片 #{ref_id}]({m.group(2)})"

        new_content = _IMAGE_MD_RE.sub(_repl, content)
        if not changed:
            return msg
        return msg.model_copy(update={"content": new_content})

    # ------------------------------------------------------------------ #
    #  文件解析状态管理                                                    #
    # ------------------------------------------------------------------ #

    async def save_file_content(self, file_id: int, content: str) -> ChatFileContent:
        """持久化解析内容，parse_status → 1"""
        existing = await self._content_mapper.get_by_file_id(file_id)
        if existing:
            await self._content_mapper.update_by_id(
                existing.id,
                {"content": content, "content_length": len(content)},
            )
            file_content = await self._content_mapper.get_by_file_id(file_id)
        else:
            file_content = await self._content_mapper.create_from_dict(
                {"file_id": file_id, "content": content, "content_length": len(content)}
            )
        await self._file_mapper.update_parse_status(file_id, 1)
        return file_content

    async def mark_parse_failed(self, file_id: int, error: str) -> None:
        """parse_status → -1"""
        await self._file_mapper.update_parse_status(file_id, -1, error)

    # ------------------------------------------------------------------ #
    #  秒传                                                                #
    # ------------------------------------------------------------------ #

    async def find_duplicate_by_md5(self, md5: str) -> Optional[ChatFile]:
        return await self._file_mapper.get_by_md5(md5)

    async def get_file_ids_by_message_ids(
            self, message_ids: List[str]
    ) -> Dict[str, List[int]]:
        """
        根据多个 message_id 批量获取 file_id 列表

        返回:
            {
                message_id1: [file_id1, file_id2],
                message_id2: [],
            }
        """
        if not message_ids:
            return {}

        return await self._msg_file_mapper.get_file_ids_by_message_ids(message_ids)

    async def get_files_map_by_message_ids(
            self, message_ids: List[str]
    ) -> Dict[str, List[ChatFile]]:
        """
        批量获取 message -> [ChatFile]
        """
        if not message_ids:
            return {}

        msg_to_file_ids = await self._msg_file_mapper.get_file_ids_by_message_ids(
            message_ids
        )
        if not msg_to_file_ids:
            return {}

        all_file_ids = list({
            fid
            for fids in msg_to_file_ids.values()
            for fid in fids
        })

        file_map = await self._file_mapper.get_by_ids(all_file_ids)

        result: Dict[str, List[ChatFile]] = {}

        for mid, fids in msg_to_file_ids.items():
            result[mid] = [
                file_map[fid]
                for fid in fids
                if fid in file_map
            ]

        return result
