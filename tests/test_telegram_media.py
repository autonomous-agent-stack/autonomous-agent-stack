"""
Telegram 媒体服务测试套件

测试覆盖：
1. 媒体附件（图片、文档、音频、视频）
2. 交互元素（按钮、键盘、callback）
3. 序列化/反序列化
4. 消息构建器
5. 降级机制
"""

import pytest
import json
import base64
from io import BytesIO

from src.autoresearch.core.services.telegram_media import (
    # 枚举
    MediaType,
    ParseMode,
    KeyboardType,

    # 数据模型
    MediaAttachment,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    RichMessage,

    # 构建器
    MessageBuilder,
    InlineKeyboardBuilder,
    ReplyKeyboardBuilder,

    # 便捷函数
    text_message,
    photo_message,
    document_message,
    with_inline_keyboard,
    with_reply_keyboard,
    remove_keyboard,

    # 服务类
    TelegramMediaService,
)


# ============================================
# 测试媒体附件
# ============================================

class TestMediaAttachment:
    """测试媒体附件"""

    def test_create_photo_with_file_path(self):
        """测试使用文件路径创建图片"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_path="/path/to/photo.jpg",
            caption="测试图片"
        )

        assert media.media_type == MediaType.PHOTO
        assert media.file_path == "/path/to/photo.jpg"
        assert media.caption == "测试图片"
        assert media.validate() is True

    def test_create_photo_with_file_data(self):
        """测试使用二进制数据创建图片"""
        data = b"fake image data"
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_data=data,
            filename="test.jpg"
        )

        assert media.media_type == MediaType.PHOTO
        assert media.file_data == data
        assert media.filename == "test.jpg"
        assert media.validate() is True

    def test_create_photo_with_file_id(self):
        """测试使用 file_id 创建图片"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_id="AgADbQExG8kxEg...",
            caption="使用 file_id"
        )

        assert media.media_type == MediaType.PHOTO
        assert media.file_id == "AgADbQExG8kxEg..."
        assert media.validate() is True

    def test_create_document(self):
        """测试创建文档"""
        media = MediaAttachment(
            media_type=MediaType.DOCUMENT,
            file_path="/path/to/document.pdf",
            filename="document.pdf",
            mime_type="application/pdf",
            caption="测试文档"
        )

        assert media.media_type == MediaType.DOCUMENT
        assert media.filename == "document.pdf"
        assert media.mime_type == "application/pdf"
        assert media.validate() is True

    def test_create_audio(self):
        """测试创建音频"""
        media = MediaAttachment(
            media_type=MediaType.AUDIO,
            file_path="/path/to/audio.mp3",
            duration=180,  # 3 分钟
            mime_type="audio/mpeg"
        )

        assert media.media_type == MediaType.AUDIO
        assert media.duration == 180
        assert media.validate() is True

    def test_create_video(self):
        """测试创建视频"""
        media = MediaAttachment(
            media_type=MediaType.VIDEO,
            file_path="/path/to/video.mp4",
            width=1920,
            height=1080,
            duration=300,  # 5 分钟
            caption="测试视频"
        )

        assert media.media_type == MediaType.VIDEO
        assert media.width == 1920
        assert media.height == 1080
        assert media.duration == 300
        assert media.validate() is True

    def test_invalid_attachment_no_source(self):
        """测试无效的附件（没有来源）"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO
        )

        assert media.validate() is False

    def test_to_telegram_dict_with_file_path(self):
        """测试转换为 Telegram API 字典（文件路径）"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_path="/path/to/photo.jpg",
            caption="测试图片"
        )

        result = media.to_telegram_dict()

        assert "path" in result
        assert result["path"] == "/path/to/photo.jpg"
        assert result["caption"] == "测试图片"

    def test_to_telegram_dict_with_file_id(self):
        """测试转换为 Telegram API 字典（file_id）"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_id="AgADbQExG8kxEg..."
        )

        result = media.to_telegram_dict()

        assert "file_id" in result
        assert result["file_id"] == "AgADbQExG8kxEg..."

    def test_to_telegram_dict_with_file_data(self):
        """测试转换为 Telegram API 字典（二进制数据）"""
        data = b"fake image data"
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_data=data
        )

        result = media.to_telegram_dict()

        assert "data" in result
        assert result["data"] == data

    def test_serialize_deserialize(self):
        """测试序列化和反序列化"""
        original = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_path="/path/to/photo.jpg",
            caption="测试图片",
            parse_mode=ParseMode.MARKDOWN
        )

        # 序列化
        serialized = original.serialize()

        assert serialized["media_type"] == "photo"
        assert serialized["file_path"] == "/path/to/photo.jpg"
        assert serialized["caption"] == "测试图片"
        assert serialized["parse_mode"] == "Markdown"

        # 反序列化
        deserialized = MediaAttachment.deserialize(serialized)

        assert deserialized.media_type == MediaType.PHOTO
        assert deserialized.file_path == "/path/to/photo.jpg"
        assert deserialized.caption == "测试图片"
        assert deserialized.parse_mode == ParseMode.MARKDOWN

    def test_serialize_with_file_data(self):
        """测试序列化二进制数据（base64）"""
        data = b"fake image data"
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_data=data
        )

        serialized = media.serialize()

        assert "file_data_base64" in serialized
        assert "file_data" not in serialized

        # 反序列化
        deserialized = MediaAttachment.deserialize(serialized)
        assert deserialized.file_data == data

    def test_serialize_with_thumbnail(self):
        """测试带缩略图的序列化"""
        thumbnail = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_id="thumb_id"
        )
        media = MediaAttachment(
            media_type=MediaType.VIDEO,
            file_id="video_id",
            thumbnail=thumbnail
        )

        serialized = media.serialize()

        assert "thumbnail" in serialized
        assert serialized["thumbnail"]["file_id"] == "thumb_id"

        # 反序列化
        deserialized = MediaAttachment.deserialize(serialized)
        assert deserialized.thumbnail.file_id == "thumb_id"


# ============================================
# 测试交互元素
# ============================================

class TestInlineKeyboardButton:
    """测试内联键盘按钮"""

    def test_callback_button(self):
        """测试回调按钮"""
        button = InlineKeyboardButton(
            text="点击我",
            callback_data="button_clicked"
        )

        assert button.text == "点击我"
        assert button.callback_data == "button_clicked"
        assert button.validate() is True

    def test_url_button(self):
        """测试 URL 按钮"""
        button = InlineKeyboardButton(
            text="访问网站",
            url="https://example.com"
        )

        assert button.text == "访问网站"
        assert button.url == "https://example.com"
        assert button.validate() is True

    def test_invalid_button_no_action(self):
        """测试无效的按钮（没有 action）"""
        button = InlineKeyboardButton(
            text="无效按钮"
        )

        assert button.validate() is False

    def test_to_dict(self):
        """测试转换为字典"""
        button = InlineKeyboardButton(
            text="点击我",
            callback_data="button_clicked"
        )

        result = button.to_dict()

        assert result["text"] == "点击我"
        assert result["callback_data"] == "button_clicked"

    def test_serialize_deserialize(self):
        """测试序列化和反序列化"""
        original = InlineKeyboardButton(
            text="点击我",
            callback_data="button_clicked"
        )

        serialized = original.serialize()
        deserialized = InlineKeyboardButton.deserialize(serialized)

        assert deserialized.text == "点击我"
        assert deserialized.callback_data == "button_clicked"


class TestInlineKeyboardMarkup:
    """测试内联键盘标记"""

    def test_create_empty_keyboard(self):
        """测试创建空键盘"""
        keyboard = InlineKeyboardMarkup()

        assert keyboard.inline_keyboard == []
        assert len(keyboard.inline_keyboard) == 0

    def test_add_button(self):
        """测试添加按钮"""
        keyboard = InlineKeyboardMarkup()
        button = InlineKeyboardButton(
            text="按钮1",
            callback_data="btn1"
        )

        keyboard.add_button(button)

        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1

    def test_add_multiple_buttons_same_row(self):
        """测试在同一行添加多个按钮"""
        keyboard = InlineKeyboardMarkup()

        keyboard.add_button(InlineKeyboardButton(text="按钮1", callback_data="btn1"))
        keyboard.add_button(InlineKeyboardButton(text="按钮2", callback_data="btn2"))

        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2

    def test_add_button_to_different_row(self):
        """测试在不同行添加按钮"""
        keyboard = InlineKeyboardMarkup()

        keyboard.add_button(InlineKeyboardButton(text="按钮1", callback_data="btn1"), row=0)
        keyboard.add_button(InlineKeyboardButton(text="按钮2", callback_data="btn2"), row=1)

        assert len(keyboard.inline_keyboard) == 2
        assert len(keyboard.inline_keyboard[0]) == 1
        assert len(keyboard.inline_keyboard[1]) == 1

    def test_add_row(self):
        """测试添加一行"""
        keyboard = InlineKeyboardMarkup()

        row = [
            InlineKeyboardButton(text="按钮1", callback_data="btn1"),
            InlineKeyboardButton(text="按钮2", callback_data="btn2")
        ]
        keyboard.add_row(row)

        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2

    def test_to_dict(self):
        """测试转换为 Telegram API 格式"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add_button(InlineKeyboardButton(text="按钮1", callback_data="btn1"))

        result = keyboard.to_dict()

        assert "inline_keyboard" in result
        assert len(result["inline_keyboard"]) == 1
        assert result["inline_keyboard"][0][0]["text"] == "按钮1"

    def test_serialize_deserialize(self):
        """测试序列化和反序列化"""
        original = InlineKeyboardMarkup()
        original.add_button(InlineKeyboardButton(text="按钮1", callback_data="btn1"))
        original.add_button(InlineKeyboardButton(text="按钮2", callback_data="btn2"))

        serialized = original.serialize()
        deserialized = InlineKeyboardMarkup.deserialize(serialized)

        assert len(deserialized.inline_keyboard) == 1
        assert len(deserialized.inline_keyboard[0]) == 2
        assert deserialized.inline_keyboard[0][0].text == "按钮1"


class TestReplyKeyboardButton:
    """测试回复键盘按钮"""

    def test_simple_button(self):
        """测试简单按钮"""
        button = ReplyKeyboardButton(text="开始")

        assert button.text == "开始"
        assert button.request_contact is False
        assert button.request_location is False

    def test_request_contact_button(self):
        """测试请求联系人的按钮"""
        button = ReplyKeyboardButton(
            text="分享联系人",
            request_contact=True
        )

        assert button.text == "分享联系人"
        assert button.request_contact is True

    def test_request_location_button(self):
        """测试请求位置的按钮"""
        button = ReplyKeyboardButton(
            text="分享位置",
            request_location=True
        )

        assert button.text == "分享位置"
        assert button.request_location is True

    def test_to_dict(self):
        """测试转换为字典"""
        button = ReplyKeyboardButton(text="开始")

        result = button.to_dict()

        assert result["text"] == "开始"
        assert result["request_contact"] is False

    def test_serialize_deserialize(self):
        """测试序列化和反序列化"""
        original = ReplyKeyboardButton(text="开始", request_contact=True)

        serialized = original.serialize()
        deserialized = ReplyKeyboardButton.deserialize(serialized)

        assert deserialized.text == "开始"
        assert deserialized.request_contact is True


class TestReplyKeyboardMarkup:
    """测试回复键盘标记"""

    def test_create_keyboard(self):
        """测试创建键盘"""
        keyboard = ReplyKeyboardMarkup()

        assert keyboard.keyboard == []
        assert keyboard.resize_keyboard is False
        assert keyboard.one_time_keyboard is False

    def test_add_button(self):
        """测试添加按钮"""
        keyboard = ReplyKeyboardMarkup()
        keyboard.add_button(ReplyKeyboardButton(text="按钮1"))

        assert len(keyboard.keyboard) == 1
        assert len(keyboard.keyboard[0]) == 1

    def test_add_row(self):
        """测试添加一行"""
        keyboard = ReplyKeyboardMarkup()
        row = [
            ReplyKeyboardButton(text="按钮1"),
            ReplyKeyboardButton(text="按钮2")
        ]
        keyboard.add_row(row)

        assert len(keyboard.keyboard) == 1
        assert len(keyboard.keyboard[0]) == 2

    def test_resize_keyboard(self):
        """测试调整键盘大小"""
        keyboard = ReplyKeyboardMarkup()
        keyboard.resize_keyboard = True

        assert keyboard.resize_keyboard is True

    def test_one_time_keyboard(self):
        """测试一次性键盘"""
        keyboard = ReplyKeyboardMarkup()
        keyboard.one_time_keyboard = True

        assert keyboard.one_time_keyboard is True

    def test_to_dict(self):
        """测试转换为 Telegram API 格式"""
        keyboard = ReplyKeyboardMarkup()
        keyboard.add_button(ReplyKeyboardButton(text="按钮1"))
        keyboard.resize_keyboard = True

        result = keyboard.to_dict()

        assert "keyboard" in result
        assert result["resize_keyboard"] is True
        assert result["keyboard"][0][0]["text"] == "按钮1"

    def test_serialize_deserialize(self):
        """测试序列化和反序列化"""
        original = ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=True
        )
        original.add_button(ReplyKeyboardButton(text="按钮1"))

        serialized = original.serialize()
        deserialized = ReplyKeyboardMarkup.deserialize(serialized)

        assert deserialized.resize_keyboard is True
        assert deserialized.one_time_keyboard is True
        assert len(deserialized.keyboard) == 1


class TestReplyKeyboardRemove:
    """测试移除回复键盘"""

    def test_create(self):
        """测试创建"""
        remove = ReplyKeyboardRemove()

        assert remove.remove_keyboard is True
        assert remove.selective is False

    def test_selective(self):
        """测试选择性移除"""
        remove = ReplyKeyboardRemove(selective=True)

        assert remove.remove_keyboard is True
        assert remove.selective is True

    def test_to_dict(self):
        """测试转换为字典"""
        remove = ReplyKeyboardRemove()

        result = remove.to_dict()

        assert result["remove_keyboard"] is True


# ============================================
# 测试富消息
# ============================================

class TestRichMessage:
    """测试富消息"""

    def test_create_text_message(self):
        """测试创建文本消息"""
        message = RichMessage(
            text="Hello, World!",
            parse_mode=ParseMode.MARKDOWN
        )

        assert message.text == "Hello, World!"
        assert message.parse_mode == ParseMode.MARKDOWN
        assert message.validate() is True

    def test_create_media_message(self):
        """测试创建媒体消息"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_path="/path/to/photo.jpg"
        )
        message = RichMessage(media=media)

        assert message.media is not None
        assert message.media.media_type == MediaType.PHOTO
        assert message.validate() is True

    def test_create_message_with_keyboard(self):
        """测试创建带键盘的消息"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add_button(InlineKeyboardButton(text="点击", callback_data="btn"))

        message = RichMessage(
            text="选择一个选项",
            reply_markup=keyboard
        )

        assert message.reply_markup is not None
        assert isinstance(message.reply_markup, InlineKeyboardMarkup)
        assert message.validate() is True

    def test_invalid_message_no_content(self):
        """测试无效的消息（没有内容）"""
        message = RichMessage()

        assert message.validate() is False

    def test_invalid_message_invalid_media(self):
        """测试无效的消息（媒体无效）"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO
        )  # 没有来源
        message = RichMessage(media=media)

        assert message.validate() is False

    def test_downgrade_media_to_text(self):
        """测试将媒体消息降级为文本"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            caption="测试图片"
        )
        message = RichMessage(
            media=media,
            reply_markup=InlineKeyboardMarkup()
        )

        downgraded = message.downgrade()

        assert downgraded.text is not None
        assert downgraded.media is None
        assert downgraded.reply_markup is None
        assert downgraded.parse_mode == ParseMode.PLAIN
        assert "图片" in downgraded.text

    def test_downgrade_text_only(self):
        """测试纯文本消息的降级（应该保持不变）"""
        message = RichMessage(
            text="纯文本消息",
            parse_mode=ParseMode.MARKDOWN
        )

        downgraded = message.downgrade()

        assert downgraded.text == "纯文本消息"
        assert downgraded.parse_mode == ParseMode.PLAIN  # 解析模式被重置

    def test_to_telegram_api_text(self):
        """测试转换为 Telegram API（文本消息）"""
        message = RichMessage(
            text="Hello, World!",
            parse_mode=ParseMode.MARKDOWN
        )

        result = message.to_telegram_api()

        assert result["text"] == "Hello, World!"
        assert result["parse_mode"] == "Markdown"

    def test_to_telegram_api_photo(self):
        """测试转换为 Telegram API（图片消息）"""
        media = MediaAttachment(
            media_type=MediaType.PHOTO,
            file_path="/path/to/photo.jpg",
            caption="测试图片"
        )
        message = RichMessage(media=media)

        result = message.to_telegram_api()

        assert result["path"] == "/path/to/photo.jpg"
        assert result["caption"] == "测试图片"

    def test_to_telegram_api_with_keyboard(self):
        """测试转换为 Telegram API（带键盘）"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add_button(InlineKeyboardButton(text="点击", callback_data="btn"))

        message = RichMessage(
            text="选择一个选项",
            reply_markup=keyboard
        )

        result = message.to_telegram_api()

        assert "reply_markup" in result
        assert "inline_keyboard" in result["reply_markup"]

    def test_serialize_deserialize(self):
        """测试序列化和反序列化"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add_button(InlineKeyboardButton(text="按钮", callback_data="btn"))

        original = RichMessage(
            text="测试消息",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

        serialized = original.serialize()
        deserialized = RichMessage.deserialize(serialized)

        assert deserialized.text == "测试消息"
        assert deserialized.parse_mode == ParseMode.MARKDOWN
        assert deserialized.disable_web_page_preview is True
        assert deserialized.reply_markup is not None


# ============================================
# 测试消息构建器
# ============================================

class TestMessageBuilder:
    """测试消息构建器"""

    def test_build_text_message(self):
        """测试构建文本消息"""
        message = (MessageBuilder()
                   .text("Hello, World!")
                   .parse_mode(ParseMode.MARKDOWN)
                   .build())

        assert message.text == "Hello, World!"
        assert message.parse_mode == ParseMode.MARKDOWN

    def test_build_photo_message(self):
        """测试构建图片消息"""
        message = (MessageBuilder()
                   .photo(file_path="/path/to/photo.jpg", caption="测试图片")
                   .build())

        assert message.media is not None
        assert message.media.media_type == MediaType.PHOTO
        assert message.media.caption == "测试图片"

    def test_build_document_message(self):
        """测试构建文档消息"""
        message = (MessageBuilder()
                   .document(
                       file_path="/path/to/doc.pdf",
                       filename="doc.pdf",
                       caption="测试文档"
                   )
                   .build())

        assert message.media is not None
        assert message.media.media_type == MediaType.DOCUMENT
        assert message.media.filename == "doc.pdf"

    def test_build_with_inline_keyboard(self):
        """测试构建带内联键盘的消息"""
        message = (MessageBuilder()
                   .text("选择一个选项")
                   .inline_keyboard()
                   .button("选项1", callback_data="opt1")
                   .button("选项2", callback_data="opt2")
                   .row()
                   .button("取消", callback_data="cancel")
                   .build())

        assert message.reply_markup is not None
        assert isinstance(message.reply_markup, InlineKeyboardMarkup)
        assert len(message.reply_markup.inline_keyboard) == 2
        assert len(message.reply_markup.inline_keyboard[0]) == 2

    def test_build_with_reply_keyboard(self):
        """测试构建带回复键盘的消息"""
        message = (MessageBuilder()
                   .text("选择一个选项")
                   .reply_keyboard()
                   .button("选项1")
                   .button("选项2")
                   .row()
                   .button("取消")
                   .resize(True)
                   .build())

        assert message.reply_markup is not None
        assert isinstance(message.reply_markup, ReplyKeyboardMarkup)
        assert message.reply_markup.resize_keyboard is True

    def test_chained_building(self):
        """测试链式构建"""
        message = (MessageBuilder()
                   .text("测试消息")
                   .parse_mode(ParseMode.MARKDOWN)
                   .disable_web_page_preview(True)
                   .disable_notification(True)
                   .reply_to(123)
                   .build())

        assert message.text == "测试消息"
        assert message.parse_mode == ParseMode.MARKDOWN
        assert message.disable_web_page_preview is True
        assert message.disable_notification is True
        assert message.reply_to_message_id == 123


# ============================================
# 测试便捷函数
# ============================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_text_message_function(self):
        """测试 text_message 函数"""
        message = text_message("Hello, World!", ParseMode.MARKDOWN)

        assert message.text == "Hello, World!"
        assert message.parse_mode == ParseMode.MARKDOWN

    def test_photo_message_function(self):
        """测试 photo_message 函数"""
        message = photo_message(
            file_path="/path/to/photo.jpg",
            caption="测试图片"
        )

        assert message.media is not None
        assert message.media.media_type == MediaType.PHOTO
        assert message.media.caption == "测试图片"

    def test_document_message_function(self):
        """测试 document_message 函数"""
        message = document_message(
            file_path="/path/to/doc.pdf",
            filename="doc.pdf"
        )

        assert message.media is not None
        assert message.media.media_type == MediaType.DOCUMENT
        assert message.media.filename == "doc.pdf"

    def test_with_inline_keyboard_function(self):
        """测试 with_inline_keyboard 函数"""
        message = text_message("选择一个选项")
        buttons = [
            [
                {"text": "选项1", "callback_data": "opt1"},
                {"text": "选项2", "callback_data": "opt2"}
            ],
            [
                {"text": "取消", "callback_data": "cancel"}
            ]
        ]

        message = with_inline_keyboard(message, buttons)

        assert message.reply_markup is not None
        assert isinstance(message.reply_markup, InlineKeyboardMarkup)
        assert len(message.reply_markup.inline_keyboard) == 2

    def test_with_reply_keyboard_function(self):
        """测试 with_reply_keyboard 函数"""
        message = text_message("选择一个选项")
        buttons = [
            ["选项1", "选项2"],
            ["取消"]
        ]

        message = with_reply_keyboard(
            message,
            buttons,
            resize=True,
            one_time=True
        )

        assert message.reply_markup is not None
        assert isinstance(message.reply_markup, ReplyKeyboardMarkup)
        assert message.reply_markup.resize_keyboard is True
        assert message.reply_markup.one_time_keyboard is True

    def test_remove_keyboard_function(self):
        """测试 remove_keyboard 函数"""
        keyboard = ReplyKeyboardMarkup()
        keyboard.add_button(ReplyKeyboardButton(text="按钮"))
        message = RichMessage(text="消息", reply_markup=keyboard)

        message = remove_keyboard(message)

        assert isinstance(message.reply_markup, ReplyKeyboardRemove)


# ============================================
# 测试服务类
# ============================================

class TestTelegramMediaService:
    """测试 Telegram 媒体服务"""

    def test_create_message_from_dict(self):
        """测试从字典创建消息"""
        service = TelegramMediaService()
        data = {
            "text": "Hello, World!",
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        message = service.create_message(data)

        assert message.text == "Hello, World!"
        assert message.parse_mode == ParseMode.MARKDOWN
        assert message.disable_web_page_preview is True

    def test_create_photo_message_from_dict(self):
        """测试从字典创建图片消息"""
        service = TelegramMediaService()
        data = {
            "type": "photo",
            "file_id": "AgADbQExG8kxEg...",
            "caption": "测试图片"
        }

        message = service.create_message(data)

        assert message.media is not None
        assert message.media.media_type == MediaType.PHOTO
        assert message.media.file_id == "AgADbQExG8kxEg..."

    def test_prepare_valid_message(self):
        """测试准备有效消息"""
        service = TelegramMediaService()
        message = RichMessage(text="Hello, World!")

        result = service.prepare_for_send(message)

        assert result["text"] == "Hello, World!"

    def test_prepare_invalid_message_without_downgrade(self):
        """测试准备无效消息（不降级）"""
        service = TelegramMediaService(auto_downgrade=False)
        message = RichMessage()  # 无效消息

        with pytest.raises(ValueError):
            service.prepare_for_send(message)

    def test_prepare_invalid_message_with_downgrade(self):
        """测试准备无效消息（降级）"""
        service = TelegramMediaService(auto_downgrade=True)
        message = RichMessage()  # 无效消息

        result = service.prepare_for_send(message)

        # 降级后的消息应该有默认文本
        assert "text" in result

    def test_serialize_message(self):
        """测试序列化消息"""
        service = TelegramMediaService()
        message = RichMessage(
            text="测试消息",
            parse_mode=ParseMode.MARKDOWN
        )

        json_str = service.serialize_message(message)

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["text"] == "测试消息"
        assert data["parse_mode"] == "Markdown"

    def test_deserialize_message(self):
        """测试反序列化消息"""
        service = TelegramMediaService()
        data = {
            "text": "测试消息",
            "parse_mode": "Markdown"
        }
        json_str = json.dumps(data)

        message = service.deserialize_message(json_str)

        assert message.text == "测试消息"
        assert message.parse_mode == ParseMode.MARKDOWN

    def test_batch_deserialize(self):
        """测试批量反序列化"""
        service = TelegramMediaService()

        messages = [
            {"text": "消息1"},
            {"text": "消息2"},
            {"text": "消息3"}
        ]
        json_list = [json.dumps(m) for m in messages]

        result = service.batch_deserialize(json_list)

        assert len(result) == 3
        assert result[0].text == "消息1"
        assert result[1].text == "消息2"
        assert result[2].text == "消息3"

    def test_builder(self):
        """测试创建构建器"""
        service = TelegramMediaService()
        builder = service.builder()

        assert isinstance(builder, MessageBuilder)

        message = builder.text("测试消息").build()

        assert message.text == "测试消息"


# ============================================
# 测试完整流程
# ============================================

class TestCompleteWorkflows:
    """测试完整工作流程"""

    def test_text_message_workflow(self):
        """测试文本消息完整流程"""
        # 构建消息
        message = (MessageBuilder()
                   .text("Hello, *World*!")
                   .parse_mode(ParseMode.MARKDOWN)
                   .build())

        # 序列化
        service = TelegramMediaService()
        json_str = service.serialize_message(message)

        # 反序列化
        restored = service.deserialize_message(json_str)

        # 准备发送
        api_params = service.prepare_for_send(restored)

        assert api_params["text"] == "Hello, *World*!"
        assert api_params["parse_mode"] == "Markdown"

    def test_photo_with_keyboard_workflow(self):
        """测试图片带键盘完整流程"""
        # 构建消息
        message = (MessageBuilder()
                   .photo(
                       file_path="/path/to/photo.jpg",
                       caption="选择一个选项"
                   )
                   .inline_keyboard()
                   .button("选项1", callback_data="opt1")
                   .button("选项2", callback_data="opt2")
                   .build())

        # 验证
        assert message.media is not None
        assert message.reply_markup is not None

        # 准备发送
        service = TelegramMediaService()
        api_params = service.prepare_for_send(message)

        assert "path" in api_params
        assert "reply_markup" in api_params

    def test_document_with_reply_keyboard_workflow(self):
        """测试文档带回复键盘完整流程"""
        # 构建消息
        message = (MessageBuilder()
                   .text("请选择")
                   .reply_keyboard()
                   .button("开始")
                   .button("设置")
                   .resize(True)
                   .one_time(True)
                   .build())

        # 准备发送
        service = TelegramMediaService()
        api_params = service.prepare_for_send(message)

        assert api_params["text"] == "请选择"
        assert "reply_markup" in api_params
        assert api_params["reply_markup"]["resize_keyboard"] is True

    def test_downgrade_workflow(self):
        """测试降级流程"""
        # 创建无效消息（媒体没有来源）
        media = MediaAttachment(media_type=MediaType.PHOTO)
        message = RichMessage(media=media)

        # 自动降级
        service = TelegramMediaService(auto_downgrade=True)
        api_params = service.prepare_for_send(message)

        # 验证降级
        assert "text" in api_params
        assert "media" not in api_params
        assert "图片" in api_params["text"]

    def test_serialize_and_restore_workflow(self):
        """测试序列化和恢复完整流程"""
        # 构建复杂消息
        message = (MessageBuilder()
                   .text("测试消息")
                   .parse_mode(ParseMode.MARKDOWN_V2)
                   .disable_web_page_preview(True)
                   .photo(
                       file_path="/path/to/photo.jpg",
                       caption="图片说明"
                   )
                   .inline_keyboard()
                   .button("按钮1", callback_data="btn1")
                   .button("按钮2", url="https://example.com")
                   .build())

        # 序列化
        service = TelegramMediaService()
        json_str = service.serialize_message(message)

        # 保存到文件（模拟）
        # with open("message.json", "w") as f:
        #     f.write(json_str)

        # 从文件恢复（模拟）
        restored = service.deserialize_message(json_str)

        # 验证恢复的消息
        assert restored.text == "测试消息"
        assert restored.parse_mode == ParseMode.MARKDOWN_V2
        assert restored.media is not None
        assert restored.reply_markup is not None

        # 准备发送
        api_params = service.prepare_for_send(restored)

        assert "text" in api_params
        assert "reply_markup" in api_params


# ============================================
# 运行测试
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
