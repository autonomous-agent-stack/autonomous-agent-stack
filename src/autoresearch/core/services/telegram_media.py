"""
Telegram 富交互与媒体适配层

提供统一的接口来处理 Telegram 的富媒体内容和交互元素。
支持图片、文件、音频、文档、按钮、callback、reply keyboard 等功能。

核心设计：
- 序列化层：将富交互元素转换为标准化的 JSON 格式
- 降级机制：不支持的内容自动降级，不直接失败
- 解耦设计：独立的 service 层，router 可以直接消费
"""

import base64
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, BinaryIO
from io import BytesIO

logger = logging.getLogger(__name__)


# ============================================
# 枚举类型定义
# ============================================

class MediaType(str, Enum):
    """媒体类型枚举"""
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    ANIMATION = "animation"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"


class ParseMode(str, Enum):
    """解析模式枚举"""
    MARKDOWN = "Markdown"
    MARKDOWN_V2 = "MarkdownV2"
    HTML = "HTML"
    PLAIN = "None"


class KeyboardType(str, Enum):
    """键盘类型枚举"""
    REPLY = "reply"
    INLINE = "inline"
    REMOVE = "remove"


# ============================================
# 数据模型
# ============================================

@dataclass
class MediaAttachment:
    """媒体附件基类"""
    media_type: MediaType
    file_id: Optional[str] = None  # Telegram file_id
    file_url: Optional[str] = None  # 文件 URL
    file_path: Optional[str] = None  # 本地文件路径
    file_data: Optional[bytes] = None  # 文件二进制数据
    caption: Optional[str] = None
    parse_mode: Optional[ParseMode] = ParseMode.PLAIN
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None  # 图片/视频宽度
    height: Optional[int] = None  # 图片/视频高度
    duration: Optional[int] = None  # 音频/视频时长（秒）
    thumbnail: Optional['MediaAttachment'] = None  # 缩略图

    def validate(self) -> bool:
        """验证附件是否有效"""
        # 至少需要一种来源
        has_source = any([
            self.file_id,
            self.file_url,
            self.file_path,
            self.file_data
        ])
        return has_source

    def to_telegram_dict(self) -> Dict[str, Any]:
        """转换为 Telegram Bot API 兼容的字典"""
        result: Dict[str, Any] = {}

        # 确定发送方式
        if self.file_data:
            # 直接发送二进制数据
            result["data"] = self.file_data
        elif self.file_path:
            # 发送本地文件
            result["path"] = self.file_path
        elif self.file_url:
            # 发送远程文件 URL
            result["url"] = self.file_url
        elif self.file_id:
            # 使用已上传的 file_id
            result["file_id"] = self.file_id

        # 添加元数据
        if self.caption:
            result["caption"] = self.caption
        if self.parse_mode != ParseMode.PLAIN:
            result["parse_mode"] = self.parse_mode.value
        if self.filename:
            result["filename"] = self.filename
        if self.mime_type:
            result["mime_type"] = self.mime_type
        if self.width:
            result["width"] = self.width
        if self.height:
            result["height"] = self.height
        if self.duration:
            result["duration"] = self.duration
        if self.thumbnail:
            result["thumbnail"] = self.thumbnail.to_telegram_dict()

        return result

    def serialize(self) -> Dict[str, Any]:
        """序列化为 JSON 兼容格式（用于持久化或传输）"""
        result = asdict(self)

        # 移除二进制数据（base64 编码）
        if self.file_data:
            result["file_data_base64"] = base64.b64encode(self.file_data).decode('utf-8')
            del result["file_data"]

        # 转换枚举为字符串
        if isinstance(result.get("media_type"), MediaType):
            result["media_type"] = result["media_type"].value
        if isinstance(result.get("parse_mode"), ParseMode):
            result["parse_mode"] = result["parse_mode"].value

        # 序列化缩略图
        if self.thumbnail:
            result["thumbnail"] = self.thumbnail.serialize()

        return result

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'MediaAttachment':
        """从 JSON 反序列化"""
        # 恢复枚举
        if "media_type" in data and isinstance(data["media_type"], str):
            data["media_type"] = MediaType(data["media_type"])
        if "parse_mode" in data and isinstance(data["parse_mode"], str):
            data["parse_mode"] = ParseMode(data["parse_mode"])

        # 恢复二进制数据
        if "file_data_base64" in data:
            data["file_data"] = base64.b64decode(data["file_data_base64"])
            del data["file_data_base64"]

        # 恢复缩略图
        if "thumbnail" in data and data["thumbnail"]:
            data["thumbnail"] = cls.deserialize(data["thumbnail"])

        return cls(**data)


@dataclass
class InlineKeyboardButton:
    """内联键盘按钮"""
    text: str
    callback_data: Optional[str] = None
    url: Optional[str] = None
    switch_inline_query: Optional[str] = None
    switch_inline_query_current_chat: Optional[str] = None
    callback_game: Optional[Dict[str, Any]] = None
    pay: bool = False

    def validate(self) -> bool:
        """验证按钮是否有效"""
        # 至少需要一个 action
        has_action = any([
            self.callback_data,
            self.url,
            self.switch_inline_query,
            self.switch_inline_query_current_chat,
            self.callback_game,
            self.pay
        ])
        return has_action

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result: Dict[str, Any] = {"text": self.text}
        if self.callback_data:
            result["callback_data"] = self.callback_data
        if self.url:
            result["url"] = self.url
        if self.switch_inline_query:
            result["switch_inline_query"] = self.switch_inline_query
        if self.switch_inline_query_current_chat:
            result["switch_inline_query_current_chat"] = self.switch_inline_query_current_chat
        if self.callback_game:
            result["callback_game"] = self.callback_game
        if self.pay:
            result["pay"] = self.pay
        return result

    def serialize(self) -> Dict[str, Any]:
        """序列化为 JSON"""
        return asdict(self)

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'InlineKeyboardButton':
        """从 JSON 反序列化"""
        return cls(**data)


@dataclass
class InlineKeyboardMarkup:
    """内联键盘标记"""
    inline_keyboard: List[List[InlineKeyboardButton]] = field(default_factory=list)

    def add_button(self, button: InlineKeyboardButton, row: int = 0) -> None:
        """添加按钮到指定行"""
        while len(self.inline_keyboard) <= row:
            self.inline_keyboard.append([])
        self.inline_keyboard[row].append(button)

    def add_row(self, buttons: List[InlineKeyboardButton]) -> None:
        """添加一行按钮"""
        self.inline_keyboard.append(buttons)

    def to_dict(self) -> Dict[str, Any]:
        """转换为 Telegram Bot API 格式"""
        return {
            "inline_keyboard": [
                [btn.to_dict() for btn in row]
                for row in self.inline_keyboard
            ]
        }

    def serialize(self) -> Dict[str, Any]:
        """序列化为 JSON"""
        return {
            "inline_keyboard": [
                [btn.serialize() for btn in row]
                for row in self.inline_keyboard
            ]
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'InlineKeyboardMarkup':
        """从 JSON 反序列化"""
        inline_keyboard = [
            [
                InlineKeyboardButton.deserialize(btn_data)
                for btn_data in row_data
            ]
            for row_data in data.get("inline_keyboard", [])
        ]
        return cls(inline_keyboard=inline_keyboard)


@dataclass
class ReplyKeyboardButton:
    """回复键盘按钮"""
    text: str
    request_contact: bool = False
    request_location: bool = False
    request_poll: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result: Dict[str, Any] = {"text": self.text}
        if self.request_contact:
            result["request_contact"] = self.request_contact
        if self.request_location:
            result["request_location"] = self.request_location
        if self.request_poll:
            result["request_poll"] = self.request_poll
        return result

    def serialize(self) -> Dict[str, Any]:
        """序列化为 JSON"""
        return asdict(self)

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'ReplyKeyboardButton':
        """从 JSON 反序列化"""
        return cls(**data)


@dataclass
class ReplyKeyboardMarkup:
    """回复键盘标记"""
    keyboard: List[List[ReplyKeyboardButton]] = field(default_factory=list)
    resize_keyboard: bool = False
    one_time_keyboard: bool = False
    selective: bool = False
    input_field_placeholder: Optional[str] = None

    def add_button(self, button: ReplyKeyboardButton, row: int = 0) -> None:
        """添加按钮到指定行"""
        while len(self.keyboard) <= row:
            self.keyboard.append([])
        self.keyboard[row].append(button)

    def add_row(self, buttons: List[ReplyKeyboardButton]) -> None:
        """添加一行按钮"""
        self.keyboard.append(buttons)

    def to_dict(self) -> Dict[str, Any]:
        """转换为 Telegram Bot API 格式"""
        result: Dict[str, Any] = {
            "keyboard": [
                [btn.to_dict() for btn in row]
                for row in self.keyboard
            ]
        }
        if self.resize_keyboard:
            result["resize_keyboard"] = self.resize_keyboard
        if self.one_time_keyboard:
            result["one_time_keyboard"] = self.one_time_keyboard
        if self.selective:
            result["selective"] = self.selective
        if self.input_field_placeholder:
            result["input_field_placeholder"] = self.input_field_placeholder
        return result

    def serialize(self) -> Dict[str, Any]:
        """序列化为 JSON"""
        return asdict(self)

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'ReplyKeyboardMarkup':
        """从 JSON 反序列化"""
        keyboard = [
            [
                ReplyKeyboardButton.deserialize(btn_data)
                for btn_data in row_data
            ]
            for row_data in data.get("keyboard", [])
        ]
        return cls(
            keyboard=keyboard,
            resize_keyboard=data.get("resize_keyboard", False),
            one_time_keyboard=data.get("one_time_keyboard", False),
            selective=data.get("selective", False),
            input_field_placeholder=data.get("input_field_placeholder")
        )


@dataclass
class ReplyKeyboardRemove:
    """移除回复键盘"""
    remove_keyboard: bool = True
    selective: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为 Telegram Bot API 格式"""
        result: Dict[str, Any] = {"remove_keyboard": self.remove_keyboard}
        if self.selective:
            result["selective"] = self.selective
        return result

    def serialize(self) -> Dict[str, Any]:
        """序列化为 JSON"""
        return asdict(self)

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'ReplyKeyboardRemove':
        """从 JSON 反序列化"""
        return cls(**data)


# 统一的键盘类型
Markup = Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove]


@dataclass
class RichMessage:
    """富消息容器

    封装文本、媒体和交互元素，支持序列化和降级。
    """
    text: Optional[str] = None
    parse_mode: Optional[ParseMode] = ParseMode.PLAIN
    disable_web_page_preview: bool = False
    disable_notification: bool = False
    media: Optional[MediaAttachment] = None
    reply_markup: Optional[Markup] = None
    reply_to_message_id: Optional[int] = None

    def validate(self) -> bool:
        """验证消息是否有效"""
        # 至少需要文本或媒体
        has_content = bool(self.text or self.media)
        if not has_content:
            return False

        # 验证媒体
        if self.media and not self.media.validate():
            logger.warning("Media attachment validation failed")
            return False

        return True

    def downgrade(self) -> Optional['RichMessage']:
        """降级处理：将富消息简化为纯文本

        Returns:
            降级后的消息，如果无法降级则返回 None
        """
        try:
            # 降级步骤：
            # 1. 移除所有媒体
            # 2. 移除所有键盘
            # 3. 简化解析模式为纯文本

            downgraded = RichMessage(
                text=self.text or "[媒体内容]",
                parse_mode=ParseMode.PLAIN,
                disable_web_page_preview=True,
                disable_notification=self.disable_notification,
                reply_to_message_id=self.reply_to_message_id
            )

            # 添加媒体描述
            if self.media:
                media_desc = f"\n\n[媒体类型: {self.media.media_type.value}]"
                if self.media.caption:
                    media_desc += f"\n说明: {self.media.caption}"
                downgraded.text += media_desc

            logger.info(f"Message downgraded: removed media and markup")
            return downgraded

        except Exception as e:
            logger.error(f"Downgrade failed: {e}")
            return None

    def to_telegram_api(self) -> Dict[str, Any]:
        """转换为 Telegram Bot API 调用参数

        Returns:
            适合直接传递给 Telegram Bot API 的字典
        """
        if not self.validate():
            logger.warning("Invalid message, attempting downgrade...")
            downgraded = self.downgrade()
            if not downgraded:
                raise ValueError("Cannot send invalid message")
            return downgraded.to_telegram_api()

        result: Dict[str, Any] = {}

        # 确保 parse_mode 是枚举类型
        parse_mode = self.parse_mode
        if isinstance(parse_mode, str):
            parse_mode = ParseMode(parse_mode)

        # 文本消息
        if self.text and not self.media:
            result["text"] = self.text
            result["parse_mode"] = parse_mode.value if parse_mode != ParseMode.PLAIN else None
            result["disable_web_page_preview"] = self.disable_web_page_preview

        # 媒体消息
        elif self.media:
            media_dict = self.media.to_telegram_dict()
            result.update(media_dict)

        # 键盘标记
        if self.reply_markup:
            result["reply_markup"] = self.reply_markup.to_dict()

        # 其他选项
        if self.disable_notification:
            result["disable_notification"] = self.disable_notification
        if self.reply_to_message_id:
            result["reply_to_message_id"] = self.reply_to_message_id

        # 清理 None 值
        return {k: v for k, v in result.items() if v is not None}

    def serialize(self) -> Dict[str, Any]:
        """序列化为 JSON 兼容格式

        用于：
        - 持久化到数据库
        - 传递给其他服务
        - 日志记录
        """
        result: Dict[str, Any] = {}

        if self.text:
            result["text"] = self.text
        if self.parse_mode != ParseMode.PLAIN:
            result["parse_mode"] = self.parse_mode.value
        if self.disable_web_page_preview:
            result["disable_web_page_preview"] = self.disable_web_page_preview
        if self.disable_notification:
            result["disable_notification"] = self.disable_notification
        if self.reply_to_message_id:
            result["reply_to_message_id"] = self.reply_to_message_id

        if self.media:
            result["media"] = self.media.serialize()

        if self.reply_markup:
            # 序列化时保存类型信息
            if isinstance(self.reply_markup, InlineKeyboardMarkup):
                result["reply_markup_type"] = "inline"
                result["reply_markup"] = self.reply_markup.serialize()
            elif isinstance(self.reply_markup, ReplyKeyboardMarkup):
                result["reply_markup_type"] = "reply"
                result["reply_markup"] = self.reply_markup.serialize()
            elif isinstance(self.reply_markup, ReplyKeyboardRemove):
                result["reply_markup_type"] = "remove"
                result["reply_markup"] = self.reply_markup.serialize()

        return result

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'RichMessage':
        """从 JSON 反序列化"""
        # 恢复解析模式
        if "parse_mode" in data and isinstance(data["parse_mode"], str):
            data["parse_mode"] = ParseMode(data["parse_mode"])

        # 恢复媒体
        media = None
        if "media" in data and data["media"]:
            media = MediaAttachment.deserialize(data["media"])

        # 恢复键盘
        reply_markup = None
        if "reply_markup" in data and data["reply_markup"]:
            markup_type = data.get("reply_markup_type", "")
            if markup_type == "inline":
                reply_markup = InlineKeyboardMarkup.deserialize(data["reply_markup"])
            elif markup_type == "reply":
                reply_markup = ReplyKeyboardMarkup.deserialize(data["reply_markup"])
            elif markup_type == "remove":
                reply_markup = ReplyKeyboardRemove.deserialize(data["reply_markup"])

        return cls(
            text=data.get("text"),
            parse_mode=data.get("parse_mode", ParseMode.PLAIN),
            disable_web_page_preview=data.get("disable_web_page_preview", False),
            disable_notification=data.get("disable_notification", False),
            media=media,
            reply_markup=reply_markup,
            reply_to_message_id=data.get("reply_to_message_id")
        )


# ============================================
# 消息构建器（Builder Pattern）
# ============================================

class MessageBuilder:
    """消息构建器 - 流式构建富消息"""

    def __init__(self):
        self._message = RichMessage()

    def text(self, text: str) -> 'MessageBuilder':
        """设置文本"""
        self._message.text = text
        return self

    def parse_mode(self, mode: Union[ParseMode, str]) -> 'MessageBuilder':
        """设置解析模式"""
        if isinstance(mode, str):
            mode = ParseMode(mode)
        self._message.parse_mode = mode
        return self

    def media(self, media: MediaAttachment) -> 'MessageBuilder':
        """添加媒体"""
        self._message.media = media
        return self

    def photo(
        self,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_id: Optional[str] = None,
        caption: Optional[str] = None
    ) -> 'MessageBuilder':
        """添加图片"""
        self._message.media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_path=file_path,
            file_url=file_url,
            file_data=file_data,
            file_id=file_id,
            caption=caption
        )
        return self

    def document(
        self,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_id: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None
    ) -> 'MessageBuilder':
        """添加文档"""
        self._message.media = MediaAttachment(
            media_type=MediaType.DOCUMENT,
            file_path=file_path,
            file_url=file_url,
            file_data=file_data,
            file_id=file_id,
            caption=caption,
            filename=filename
        )
        return self

    def inline_keyboard(self) -> 'InlineKeyboardBuilder':
        """创建内联键盘"""
        return InlineKeyboardBuilder(self)

    def reply_keyboard(self) -> 'ReplyKeyboardBuilder':
        """创建回复键盘"""
        return ReplyKeyboardBuilder(self)

    def disable_web_page_preview(self, disable: bool = True) -> 'MessageBuilder':
        """禁用网页预览"""
        self._message.disable_web_page_preview = disable
        return self

    def disable_notification(self, disable: bool = True) -> 'MessageBuilder':
        """禁用通知"""
        self._message.disable_notification = disable
        return self

    def reply_to(self, message_id: int) -> 'MessageBuilder':
        """回复到指定消息"""
        self._message.reply_to_message_id = message_id
        return self

    def build(self) -> RichMessage:
        """构建消息"""
        return self._message


class InlineKeyboardBuilder:
    """内联键盘构建器"""

    def __init__(self, message_builder: MessageBuilder):
        self._message_builder = message_builder
        self._keyboard = InlineKeyboardMarkup()
        self._current_row: List[InlineKeyboardButton] = []
        self._row_index = 0

    def button(
        self,
        text: str,
        callback_data: Optional[str] = None,
        url: Optional[str] = None
    ) -> 'InlineKeyboardBuilder':
        """添加按钮"""
        button = InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
            url=url
        )
        self._keyboard.add_button(button, self._row_index)
        return self

    def row(self) -> 'InlineKeyboardBuilder':
        """开始新行"""
        self._row_index += 1
        return self

    def build(self) -> MessageBuilder:
        """完成键盘构建"""
        self._message_builder._message.reply_markup = self._keyboard
        return self._message_builder


class ReplyKeyboardBuilder:
    """回复键盘构建器"""

    def __init__(self, message_builder: MessageBuilder):
        self._message_builder = message_builder
        self._keyboard = ReplyKeyboardMarkup()
        self._row_index = 0

    def button(
        self,
        text: str,
        request_contact: bool = False,
        request_location: bool = False
    ) -> 'ReplyKeyboardBuilder':
        """添加按钮"""
        button = ReplyKeyboardButton(
            text=text,
            request_contact=request_contact,
            request_location=request_location
        )
        self._keyboard.add_button(button, self._row_index)
        return self

    def row(self) -> 'ReplyKeyboardBuilder':
        """开始新行"""
        self._row_index += 1
        return self

    def resize(self, resize: bool = True) -> 'ReplyKeyboardBuilder':
        """调整键盘大小"""
        self._keyboard.resize_keyboard = resize
        return self

    def one_time(self, one_time: bool = True) -> 'ReplyKeyboardBuilder':
        """一次性键盘"""
        self._keyboard.one_time_keyboard = one_time
        return self

    def build(self) -> MessageBuilder:
        """完成键盘构建"""
        self._message_builder._message.reply_markup = self._keyboard
        return self._message_builder


# ============================================
# 便捷函数
# ============================================

def text_message(
    text: str,
    parse_mode: Union[ParseMode, str] = ParseMode.PLAIN,
    **kwargs
) -> RichMessage:
    """创建纯文本消息"""
    if isinstance(parse_mode, str):
        parse_mode = ParseMode(parse_mode)
    return RichMessage(text=text, parse_mode=parse_mode, **kwargs)


def photo_message(
    file_path: Optional[str] = None,
    file_url: Optional[str] = None,
    file_data: Optional[bytes] = None,
    file_id: Optional[str] = None,
    caption: Optional[str] = None,
    **kwargs
) -> RichMessage:
    """创建图片消息"""
    return RichMessage(
        media=MediaAttachment(
            media_type=MediaType.PHOTO,
            file_path=file_path,
            file_url=file_url,
            file_data=file_data,
            file_id=file_id,
            caption=caption
        ),
        **kwargs
    )


def document_message(
    file_path: Optional[str] = None,
    file_url: Optional[str] = None,
    file_data: Optional[bytes] = None,
    file_id: Optional[str] = None,
    caption: Optional[str] = None,
    filename: Optional[str] = None,
    **kwargs
) -> RichMessage:
    """创建文档消息"""
    return RichMessage(
        media=MediaAttachment(
            media_type=MediaType.DOCUMENT,
            file_path=file_path,
            file_url=file_url,
            file_data=file_data,
            file_id=file_id,
            caption=caption,
            filename=filename
        ),
        **kwargs
    )


def with_inline_keyboard(
    message: RichMessage,
    buttons: List[List[Dict[str, Any]]]
) -> RichMessage:
    """为消息添加内联键盘

    Args:
        message: 原始消息
        buttons: 按钮列表，格式: [[{text, callback_data, url}, ...], ...]

    Returns:
        带键盘的消息
    """
    inline_keyboard = InlineKeyboardMarkup()

    for row_data in buttons:
        row = []
        for btn_data in row_data:
            button = InlineKeyboardButton.deserialize(btn_data)
            row.append(button)
        inline_keyboard.add_row(row)

    message.reply_markup = inline_keyboard
    return message


def with_reply_keyboard(
    message: RichMessage,
    buttons: List[List[str]],
    resize: bool = False,
    one_time: bool = False
) -> RichMessage:
    """为消息添加回复键盘

    Args:
        message: 原始消息
        buttons: 按钮文本列表，格式: [["Button1", "Button2"], ...]
        resize: 是否调整键盘大小
        one_time: 是否一次性键盘

    Returns:
        带键盘的消息
    """
    reply_keyboard = ReplyKeyboardMarkup(
        resize_keyboard=resize,
        one_time_keyboard=one_time
    )

    for row_texts in buttons:
        row = []
        for text in row_texts:
            button = ReplyKeyboardButton(text=text)
            row.append(button)
        reply_keyboard.add_row(row)

    message.reply_markup = reply_keyboard
    return message


def remove_keyboard(message: RichMessage) -> RichMessage:
    """移除回复键盘

    Args:
        message: 原始消息

    Returns:
        带移除指令的消息
    """
    message.reply_markup = ReplyKeyboardRemove()
    return message


# ============================================
# 主服务类
# ============================================

class TelegramMediaService:
    """Telegram 媒体服务

    核心功能：
    1. 构建和验证富消息
    2. 序列化和反序列化
    3. 自动降级处理
    4. 提供便捷的构建器 API
    """

    def __init__(self, auto_downgrade: bool = True):
        """
        Args:
            auto_downgrade: 是否自动降级无效的消息
        """
        self.auto_downgrade = auto_downgrade

    def create_message(self, message_data: Dict[str, Any]) -> RichMessage:
        """从字典创建消息

        Args:
            message_data: 消息数据（可以是 API 返回的格式或序列化格式）

        Returns:
            RichMessage 对象
        """
        # 尝试反序列化
        try:
            return RichMessage.deserialize(message_data)
        except Exception as e:
            logger.warning(f"Failed to deserialize message: {e}, creating from scratch")

        # 从 API 格式创建
        message = RichMessage()

        # 文本
        if "text" in message_data:
            message.text = message_data["text"]
        if "parse_mode" in message_data:
            message.parse_mode = ParseMode(message_data["parse_mode"])

        # 媒体
        media_type = message_data.get("type") or message_data.get("media_type")
        if media_type:
            media = MediaAttachment(
                media_type=MediaType(media_type),
                file_id=message_data.get("file_id"),
                file_url=message_data.get("file_url"),
                caption=message_data.get("caption"),
                filename=message_data.get("filename")
            )
            message.media = media

        # 键盘
        if "reply_markup" in message_data:
            markup_data = message_data["reply_markup"]
            if "inline_keyboard" in markup_data:
                message.reply_markup = InlineKeyboardMarkup.deserialize(markup_data)
            elif "keyboard" in markup_data:
                message.reply_markup = ReplyKeyboardMarkup.deserialize(markup_data)
            elif markup_data.get("remove_keyboard"):
                message.reply_markup = ReplyKeyboardRemove.deserialize(markup_data)

        return message

    def prepare_for_send(self, message: RichMessage) -> Dict[str, Any]:
        """准备消息用于发送

        Args:
            message: 富消息对象

        Returns:
            适合 Telegram Bot API 的参数字典

        Raises:
            ValueError: 如果消息无效且无法降级
        """
        if not message.validate():
            if self.auto_downgrade:
                logger.info("Message invalid, attempting downgrade...")
                downgraded = message.downgrade()
                if downgraded:
                    return downgraded.to_telegram_api()
            raise ValueError("Invalid message and downgrade failed")

        return message.to_telegram_api()

    def serialize_message(self, message: RichMessage) -> str:
        """序列化消息为 JSON 字符串

        Args:
            message: 富消息对象

        Returns:
            JSON 字符串
        """
        return json.dumps(message.serialize(), ensure_ascii=False, indent=2)

    def deserialize_message(self, json_str: str) -> RichMessage:
        """从 JSON 字符串反序列化消息

        Args:
            json_str: JSON 字符串

        Returns:
            富消息对象
        """
        data = json.loads(json_str)
        return RichMessage.deserialize(data)

    def batch_deserialize(self, json_list: List[str]) -> List[RichMessage]:
        """批量反序列化消息

        Args:
            json_list: JSON 字符串列表

        Returns:
            富消息对象列表
        """
        messages = []
        for json_str in json_list:
            try:
                message = self.deserialize_message(json_str)
                messages.append(message)
            except Exception as e:
                logger.error(f"Failed to deserialize message: {e}")
        return messages

    def builder(self) -> MessageBuilder:
        """创建消息构建器

        Returns:
            MessageBuilder 实例
        """
        return MessageBuilder()


# ============================================
# 导出
# ============================================

__all__ = [
    # 枚举
    "MediaType",
    "ParseMode",
    "KeyboardType",

    # 数据模型
    "MediaAttachment",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "ReplyKeyboardButton",
    "ReplyKeyboardMarkup",
    "ReplyKeyboardRemove",
    "Markup",
    "RichMessage",

    # 构建器
    "MessageBuilder",
    "InlineKeyboardBuilder",
    "ReplyKeyboardBuilder",

    # 便捷函数
    "text_message",
    "photo_message",
    "document_message",
    "with_inline_keyboard",
    "with_reply_keyboard",
    "remove_keyboard",

    # 服务类
    "TelegramMediaService",
]
