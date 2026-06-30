import asyncio
import email as email_lib
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk

from app.core.config import settings
from app.core.logging_config import get_logger
from app.deps.db import get_db_session
from app.mappers.chat_file_mapper import ChatFileMapper
from app.mappers.chat_message_mapper import ChatMessageMapper
from app.mappers.user_email_agent_mapper import UserEmailAgentMapper
from app.mappers.user_mapper import UserMapper
from app.models.chat_message import ChatMessage
from app.schemas.dto.langchian import ValidAgent
from app.services.agent_service import AgentService
from app.services.chat_file_service import ChatFileService
from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.services.storage import get_file_uploader
from app.utils.langchain.agent_util import get_langchian_agent

logger = get_logger(__name__)

# 邮件收图：仅接收模型可识别的常见格式（与 message_builder.IMAGE_EXTENSIONS 对齐）
_EMAIL_IMAGE_EXT_BY_SUBTYPE = {
    "jpeg": ".jpg",
    "jpg": ".jpg",
    "png": ".png",
    "gif": ".gif",
    "webp": ".webp",
}
_EMAIL_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 单图上限 5MB（服务器 2c/2G，控制内存）
_EMAIL_IMAGE_MAX_COUNT = 6                # 单封邮件最多取 6 张


def _smtp_send(from_addr: str, to_addr: str, raw_message: str) -> None:
    """按 EMAIL_SMTP_SECURITY 选择 SSL(隐式) 或 STARTTLS 连接发信。

    Gmail/Outlook 587 走 STARTTLS，163/QQ 465 走隐式 SSL。
    """
    if settings.EMAIL_SMTP_SECURITY == "ssl":
        server = smtplib.SMTP_SSL(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT)
    else:  # starttls
        server = smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT)
        server.starttls()
    with server:
        server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
        server.sendmail(from_addr, to_addr, raw_message)


class EmailPollingService:

    async def poll(self):
        if not settings.EMAIL_ENABLED:
            return
        try:
            loop = asyncio.get_event_loop()
            emails = await loop.run_in_executor(None, self._sync_fetch_unread)
            for email_data in emails:
                try:
                    await self._process_email(email_data)
                except Exception as e:
                    logger.error(f"处理邮件失败: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"邮件轮询失败: {e}", exc_info=True)

    async def _process_email(self, email_data: dict):
        sender = email_data["sender"].lower().strip()
        # 处理 "Name <email>" 格式
        if "<" in sender and ">" in sender:
            sender = sender.split("<")[1].rstrip(">").strip()

        # 1. 按 sender 查找 User
        async with get_db_session() as db:
            user = await UserMapper(db).get_by_email(sender)
        if not user:
            logger.info(f"忽略非注册用户邮件: {sender}")
            return

        # 2. 查找该用户的邮件 Agent 配置
        async with get_db_session() as db:
            config = await UserEmailAgentMapper(db).get_by_user_id(user.id)
        if not config or not config.is_enabled:
            logger.info(f"用户 {sender} 未配置邮件 Agent 或已禁用")
            return

        # 3. 若无 session，自动创建并写入
        if not config.session_id:
            async with get_db_session() as db:
                session = await SessionService(db).create(
                    agent_id=config.agent_id,
                    user_id=user.id,
                    title=f"邮件对话 - {user.email}",
                )
                await UserEmailAgentMapper(db).update_by_id(
                    config.id, {"session_id": session.id}
                )
                config.session_id = session.id

        session_id = config.session_id

        # 4. 持久化 human 消息
        human_msg_id = str(uuid4())
        async with get_db_session() as db:
            mapper = ChatMessageMapper(db)
            last = await mapper.get_last_message_by_session(session_id)
            parent_id = last.id if last else None
            await mapper._create_entity(ChatMessage(
                id=human_msg_id,
                session_id=session_id,
                user_id=user.id,
                parent_id=parent_id,
                type="human",
                content=email_data["body"],
            ))

        # 4.5 保存邮件图片并关联到 human 消息
        #     之后 inject_files_into_messages 会自动 base64 注入，模型即可看到图片
        images = email_data.get("images") or []
        if images:
            try:
                async with get_db_session() as db:
                    await self._save_email_images(
                        db,
                        images,
                        user_id=user.id,
                        session_id=session_id,
                        message_id=human_msg_id,
                    )
            except Exception as e:
                logger.error(f"保存邮件图片失败: {e}", exc_info=True)

        # 5. 构建 Agent
        async with get_db_session() as db:
            agent_data = await AgentService(db).get_full_agent(config.agent_id, user.id)
        agent = await get_langchian_agent(ValidAgent.model_validate(agent_data), session_id=session_id)

        # 6. 拉历史 + 注入文件内容（与普通聊天一致）
        history = await ChatService.fetch_history(session_id, parent_id=human_msg_id)
        async with get_db_session() as db:
            history = await ChatFileService(db).inject_files_into_messages(history, user_id=user.id)

        # 7. 走流式 chat：所有 AI/Tool 消息由 ChatService 内部统一落库
        #    （含 parent_id 链、图片 markdown 注入、abort 兜底持久化）
        chat_service = ChatService()
        reply_text: Optional[str] = None
        try:
            async for chunk, _parent in chat_service.chat(
                session_id=session_id,
                user_id=user.id,
                agent=agent,
                messages=history,
                leaf_message_id=human_msg_id,
            ):
                if chunk is None:
                    # 邮件场景不支持人工审批，遇到 __interrupt__ 直接结束
                    break
                # 只取"完整 AI 消息"（不要流式 chunk），最后一条作为邮件回复正文
                if isinstance(chunk, AIMessage) and not isinstance(chunk, AIMessageChunk):
                    content = chunk.content if isinstance(chunk.content, str) else ""
                    if content:
                        reply_text = content
        except Exception as e:
            logger.error(f"邮件 Agent 推理失败: {e}", exc_info=True)
            return

        # 8. 发邮件回复（只用最后一条完整 AI 消息）
        if reply_text:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._sync_send_reply, email_data, reply_text
            )
            logger.info(f"已回复邮件给 {sender}")
        else:
            logger.warning(f"未产生 AI 回复，跳过发送：{sender}")

    async def _save_email_images(
        self,
        db,
        images: List[dict],
        user_id: int,
        session_id: str,
        message_id: str,
    ) -> None:
        """把邮件图片落盘、建 ChatFile 行并关联到指定消息。"""
        uploader = get_file_uploader()
        file_mapper = ChatFileMapper(db)
        file_ids: List[int] = []

        for img in images:
            object_key = await uploader.save_bytes(img["bytes"], img["ext"])
            chat_file = await file_mapper.create_from_dict({
                "file_name": img["filename"],
                "file_ext": img["ext"],
                "file_size": len(img["bytes"]),
                "content_type": img["content_type"],
                "storage_type": uploader.storage_type,
                "object_key": object_key,
                "md5": None,
                "upload_user_id": user_id,
                "session_id": session_id,
                "parse_status": 1,  # 图片无需文本解析
            })
            file_ids.append(chat_file.id)  # create_from_dict 已 flush+refresh，id 可用

        if file_ids:
            await ChatFileService(db).attach_files_to_message(message_id, file_ids)

    @staticmethod
    def _extract_image_part(part) -> Optional[dict]:
        """从邮件分段提取图片，返回 None 表示跳过（格式不支持/超限/空）。"""
        subtype = (part.get_content_subtype() or "").lower()
        ext = _EMAIL_IMAGE_EXT_BY_SUBTYPE.get(subtype)
        if not ext:
            return None
        payload = part.get_payload(decode=True)
        if not payload:
            return None
        if len(payload) > _EMAIL_IMAGE_MAX_BYTES:
            logger.warning(
                "邮件图片超过 %dMB，跳过", _EMAIL_IMAGE_MAX_BYTES // 1024 // 1024
            )
            return None
        return {
            "filename": part.get_filename() or f"email_image{ext}",
            "ext": ext,
            "content_type": part.get_content_type(),
            "bytes": payload,
        }

    def _sync_fetch_unread(self) -> List[dict]:
        results = []
        try:
            mail = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_HOST, settings.EMAIL_IMAP_PORT)
            mail.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)

            # 发送客户端身份信息（163/QQ 收信必需，Gmail/Outlook 不需要）
            if settings.EMAIL_IMAP_ID:
                imaplib.Commands['ID'] = ('AUTH',)
                args = ("name", "MyEmailClient", "contact", settings.EMAIL_USERNAME, "version", "1.0.0", "vendor",
                        "myclient")
                typ, dat = mail._simple_command('ID', '("' + '" "'.join(args) + '")')
                mail._untagged_response(typ, dat, 'ID')

            status, data = mail.select("INBOX")
            if status != "OK":
                raise Exception(f"选择 INBOX 失败: {data}")

            _, data = mail.search(None, "UNSEEN")
            mail_ids = data[0].split()

            for mail_id in mail_ids:
                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)

                sender = msg.get("From", "")
                subject = msg.get("Subject", "")
                message_id = msg.get("Message-ID", "")

                body = ""
                images: List[dict] = []
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdisp = str(part.get("Content-Disposition") or "").lower()
                        if ctype == "text/plain" and "attachment" not in cdisp and not body:
                            payload = part.get_payload(decode=True)
                            if payload is not None:
                                charset = part.get_content_charset() or "utf-8"
                                body = payload.decode(charset, errors="replace")
                        elif ctype.startswith("image/") and len(images) < _EMAIL_IMAGE_MAX_COUNT:
                            img = self._extract_image_part(part)
                            if img:
                                images.append(img)
                else:
                    payload = msg.get_payload(decode=True)
                    if payload is not None:
                        charset = msg.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")

                results.append({
                    "sender": sender,
                    "subject": subject,
                    "body": body.strip(),
                    "message_id": message_id,
                    "images": images,
                })

                # 标记已读
                mail.store(mail_id, "+FLAGS", "\\Seen")

            mail.logout()
        except Exception as e:
            logger.error(f"IMAP 收信失败: {e}", exc_info=True)
        return results

    def _sync_send_reply(self, original_email: dict, reply_text: str):
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.EMAIL_ADDRESS
            msg["To"] = original_email["sender"]
            msg["Subject"] = f"Re: {original_email.get('subject', '')}"
            if original_email.get("message_id"):
                msg["In-Reply-To"] = original_email["message_id"]
                msg["References"] = original_email["message_id"]

            msg.attach(MIMEText(reply_text, "plain", "utf-8"))

            _smtp_send(settings.EMAIL_ADDRESS, original_email["sender"], msg.as_string())
        except Exception as e:
            logger.error(f"SMTP 发信失败: {e}", exc_info=True)


def _sync_send_simple_email(to_email: str, subject: str, body: str) -> bool:
    """发送简单通知邮件（不依赖实例，直接使用全局配置）"""
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        _smtp_send(settings.EMAIL_ADDRESS, to_email, msg.as_string())
        logger.info(f"通知邮件已发送至 {to_email}")
        return True
    except Exception as e:
        logger.error(f"发送通知邮件失败: {e}", exc_info=True)
        return False


async def send_notification_email(to_email: str, subject: str, body: str) -> bool:
    """异步发送通知邮件。返回是否实际发送成功。

    注意：不依赖 EMAIL_ENABLED（那是入站邮件轮询的开关），
    出站通知只要配置了 SMTP 凭据即可发送。
    """
    if not (settings.EMAIL_ADDRESS and settings.EMAIL_PASSWORD):
        logger.warning("未配置 SMTP 凭据，跳过通知邮件发送")
        return False
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _sync_send_simple_email, to_email, subject, body
    )
