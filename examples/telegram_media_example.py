"""
Telegram 媒体服务使用示例

演示如何使用 telegram_media 服务层创建和发送各种类型的消息。
"""

import asyncio
import sys
sys.path.insert(0, '..')

from src.autoresearch.core.services.telegram_media import (
    # 枚举
    MediaType,
    ParseMode,

    # 数据模型
    MediaAttachment,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardButton,
    RichMessage,

    # 构建器
    MessageBuilder,

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


def example_1_simple_text():
    """示例 1：简单的文本消息"""
    print("\n" + "="*60)
    print("示例 1：简单的文本消息")
    print("="*60)

    # 创建文本消息
    message = text_message(
        "Hello, *World*!",
        parse_mode="Markdown"
    )

    # 准备发送
    service = TelegramMediaService()
    api_params = service.prepare_for_send(message)

    print(f"消息文本: {message.text}")
    print(f"解析模式: {message.parse_mode.value}")
    print(f"API 参数: {api_params}")
    print("✓ 示例 1 完成")


def example_2_photo_with_caption():
    """示例 2：带说明的图片"""
    print("\n" + "="*60)
    print("示例 2：带说明的图片")
    print("="*60)

    # 使用构建器创建图片消息
    message = (MessageBuilder()
        .photo(
            file_path="/path/to/photo.jpg",
            caption="这是一张美丽的 *风景照* 📸",
            filename="landscape.jpg"
        )
        .parse_mode("Markdown")
        .build())

    # 准备发送
    service = TelegramMediaService()
    api_params = service.prepare_for_send(message)

    print(f"媒体类型: {message.media.media_type.value}")
    print(f"文件路径: {message.media.file_path}")
    print(f"说明: {message.media.caption}")
    print(f"API 参数: {api_params}")
    print("✓ 示例 2 完成")


def example_3_inline_keyboard():
    """示例 3：带内联键盘的消息"""
    print("\n" + "="*60)
    print("示例 3：带内联键盘的消息")
    print("="*60)

    # 使用构建器创建带按钮的消息
    message = (MessageBuilder()
        .text("请选择一个操作：")
        .inline_keyboard()
        .button("📊 查看数据", callback_data="view_data")
        .button("⚙️ 设置", callback_data="settings")
        .row()
        .button("🔔 通知", callback_data="notifications")
        .button("❓ 帮助", callback_data="help")
        .row()
        .button("❌ 取消", callback_data="cancel")
        .build()
        .build())

    # 准备发送
    service = TelegramMediaService()
    api_params = service.prepare_for_send(message)

    print(f"文本: {message.text}")
    print(f"按钮数量: {len(message.reply_markup.inline_keyboard)}")
    print(f"第一行按钮: {len(message.reply_markup.inline_keyboard[0])}")
    print(f"API 参数: {api_params}")
    print("✓ 示例 3 完成")


def example_4_reply_keyboard():
    """示例 4：带回复键盘的消息"""
    print("\n" + "="*60)
    print("示例 4：带回复键盘的消息")
    print("="*60)

    # 使用构建器创建带回复键盘的消息
    message = (MessageBuilder()
        .text("请选择主菜单：")
        .reply_keyboard()
        .button("🏠 首页")
        .button("📱 个人中心")
        .row()
        .button("⭐ 收藏")
        .button("🔍 搜索")
        .row()
        .button("⚙️ 设置")
        .resize(True)
        .one_time(True)
        .build()
        .build())

    # 准备发送
    service = TelegramMediaService()
    api_params = service.prepare_for_send(message)

    print(f"文本: {message.text}")
    print(f"键盘行数: {len(message.reply_markup.keyboard)}")
    print(f"调整大小: {message.reply_markup.resize_keyboard}")
    print(f"一次性: {message.reply_markup.one_time_keyboard}")
    print(f"API 参数: {api_params}")
    print("✓ 示例 4 完成")


def example_5_document_with_buttons():
    """示例 5：带按钮的文档"""
    print("\n" + "="*60)
    print("示例 5：带按钮的文档")
    print("="*60)

    # 创建文档消息
    message = (MessageBuilder()
        .document(
            file_path="/path/to/report.pdf",
            filename="monthly_report.pdf",
            caption="📄 2024年3月月报"
        )
        .build())

    # 添加内联键盘
    message = with_inline_keyboard(message, [
        [
            {"text": "📥 下载", "callback_data": "download"},
            {"text": "📤 分享", "callback_data": "share"}
        ],
        [
            {"text": "🔗 链接", "url": "https://example.com/report.pdf"}
        ]
    ])

    # 准备发送
    service = TelegramMediaService()
    api_params = service.prepare_for_send(message)

    print(f"文档类型: {message.media.media_type.value}")
    print(f"文件名: {message.media.filename}")
    print(f"说明: {message.media.caption}")
    print(f"按钮行数: {len(message.reply_markup.inline_keyboard)}")
    print(f"API 参数: {api_params}")
    print("✓ 示例 5 完成")


def example_6_complex_message():
    """示例 6：复杂消息（多个选项）"""
    print("\n" + "="*60)
    print("示例 6：复杂消息（多个选项）")
    print("="*60)

    # 创建复杂消息
    message = (MessageBuilder()
        .text(
            "🎉 欢迎使用我们的服务！\\n\\n"
            "请选择您需要的功能："
        )
        .parse_mode("Markdown")
        .disable_web_page_preview(True)
        .inline_keyboard()
        .button("📊 数据分析", callback_data="analytics")
        .button("📈 报告生成", callback_data="reports")
        .row()
        .button("👥 用户管理", callback_data="users")
        .button("💬 客服支持", callback_data="support")
        .row()
        .button("📚 文档", url="https://docs.example.com")
        .button("❓ 帮助", callback_data="help")
        .build()
        .build())

    # 准备发送
    service = TelegramMediaService()
    api_params = service.prepare_for_send(message)

    print(f"文本长度: {len(message.text)}")
    print(f"按钮总数: {sum(len(row) for row in message.reply_markup.inline_keyboard)}")
    print(f"包含 URL: {any(btn.url for row in message.reply_markup.inline_keyboard for btn in row)}")
    print(f"API 参数: {api_params}")
    print("✓ 示例 6 完成")


def example_7_serialization():
    """示例 7：序列化和反序列化"""
    print("\n" + "="*60)
    print("示例 7：序列化和反序列化")
    print("="*60)

    # 创建消息
    message = (MessageBuilder()
        .text("测试消息")
        .parse_mode("Markdown")
        .inline_keyboard()
        .button("按钮1", callback_data="btn1")
        .button("按钮2", callback_data="btn2")
        .build()
        .build())

    # 序列化
    service = TelegramMediaService()
    json_str = service.serialize_message(message)

    print(f"原始消息文本: {message.text}")
    print(f"序列化长度: {len(json_str)} bytes")
    print(f"序列化片段: {json_str[:100]}...")

    # 反序列化
    restored = service.deserialize_message(json_str)

    print(f"恢复消息文本: {restored.text}")
    print(f"恢复按钮数: {len(restored.reply_markup.inline_keyboard[0])}")
    print(f"验证一致性: {restored.text == message.text}")
    print("✓ 示例 7 完成")


def example_8_downgrade():
    """示例 8：降级机制"""
    print("\n" + "="*60)
    print("示例 8：降级机制")
    print("="*60)

    # 创建无效消息（媒体没有来源）
    invalid_media = MediaAttachment(
        media_type=MediaType.PHOTO,
        caption="测试图片"
    )
    invalid_message = RichMessage(media=invalid_media)

    print(f"原始消息有效: {invalid_message.validate()}")

    # 降级
    service = TelegramMediaService(auto_downgrade=True)
    downgraded = invalid_message.downgrade()

    print(f"降级后消息有效: {downgraded.validate()}")
    print(f"降级后文本: {downgraded.text}")
    print(f"降级后媒体: {downgraded.media}")

    # 准备发送
    api_params = service.prepare_for_send(invalid_message)
    print(f"API 参数: {api_params}")
    print("✓ 示例 8 完成")


def example_9_multiple_media_types():
    """示例 9：多种媒体类型"""
    print("\n" + "="*60)
    print("示例 9：多种媒体类型")
    print("="*60)

    service = TelegramMediaService()

    # 图片
    photo_msg = photo_message(
        file_path="/path/to/photo.jpg",
        caption="这是一张图片"
    )
    print(f"✓ 图片: {photo_msg.media.media_type.value}")

    # 视频
    video_msg = MessageBuilder().media(
        MediaAttachment(
            media_type=MediaType.VIDEO,
            file_path="/path/to/video.mp4",
            duration=300,
            caption="这是一段视频"
        )
    ).build()
    print(f"✓ 视频: {video_msg.media.media_type.value}")

    # 音频
    audio_msg = MessageBuilder().media(
        MediaAttachment(
            media_type=MediaType.AUDIO,
            file_path="/path/to/audio.mp3",
            duration=180,
            caption="这是一段音频"
        )
    ).build()
    print(f"✓ 音频: {audio_msg.media.media_type.value}")

    # 文档
    doc_msg = document_message(
        file_path="/path/to/document.pdf",
        filename="document.pdf",
        caption="这是一个文档"
    )
    print(f"✓ 文档: {doc_msg.media.media_type.value}")

    print("✓ 示例 9 完成")


def example_10_url_and_callback_mix():
    """示例 10：URL 和 Callback 按钮混合"""
    print("\n" + "="*60)
    print("示例 10：URL 和 Callback 按钮混合")
    print("="*60)

    # 创建混合按钮
    message = (MessageBuilder()
        .text("选择您喜欢的平台：")
        .inline_keyboard()
        .button("GitHub", url="https://github.com")
        .button("Twitter", url="https://twitter.com")
        .row()
        .button("关注", callback_data="follow")
        .button("分享", callback_data="share")
        .row()
        .button("取消", callback_data="cancel")
        .build()
        .build())

    # 统计按钮类型
    callback_count = sum(
        1 for row in message.reply_markup.inline_keyboard
        for btn in row if btn.callback_data
    )
    url_count = sum(
        1 for row in message.reply_markup.inline_keyboard
        for btn in row if btn.url
    )

    print(f"Callback 按钮: {callback_count}")
    print(f"URL 按钮: {url_count}")
    print(f"总按钮数: {callback_count + url_count}")
    print("✓ 示例 10 完成")


def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("Telegram 媒体服务示例集")
    print("="*60)

    examples = [
        example_1_simple_text,
        example_2_photo_with_caption,
        example_3_inline_keyboard,
        example_4_reply_keyboard,
        example_5_document_with_buttons,
        example_6_complex_message,
        example_7_serialization,
        example_8_downgrade,
        example_9_multiple_media_types,
        example_10_url_and_callback_mix,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"❌ 示例失败: {e}")

    print("\n" + "="*60)
    print("所有示例运行完成！")
    print("="*60)


if __name__ == "__main__":
    main()
