# Telegram 富交互与媒体适配层

## 概述

这是一个独立的 Telegram 富交互与媒体适配服务层，提供统一的接口来处理 Telegram 的富媒体内容和交互元素。

**核心特性：**
- ✅ 支持所有媒体类型（图片、视频、音频、文档等）
- ✅ 支持所有交互元素（按钮、键盘、callback）
- ✅ 完整的序列化/反序列化支持
- ✅ 自动降级机制（不支持的内容不会直接失败）
- ✅ 流式构建器 API（Builder Pattern）
- ✅ 类型安全（完整的类型注解）
- ✅ 与 Telegram Bot API 完全兼容

## 安装

```bash
# 将服务模块添加到项目中
cp src/autoresearch/core/services/telegram_media.py <your_project_path>
```

## 快速开始

### 1. 创建简单的文本消息

```python
from src.autoresearch.core.services.telegram_media import (
    text_message, TelegramMediaService
)

# 创建文本消息
message = text_message("Hello, World!", parse_mode="Markdown")

# 准备发送
service = TelegramMediaService()
api_params = service.prepare_for_send(message)

# 使用 Telegram Bot API 发送
# await bot.send_message(**api_params)
```

### 2. 创建图片消息

```python
from src.autoresearch.core.services.telegram_media import (
    MessageBuilder, MediaType
)

# 使用构建器创建图片消息
message = (MessageBuilder()
    .photo(
        file_path="/path/to/photo.jpg",
        caption="这是一张测试图片"
    )
    .build())

# 准备发送
service = TelegramMediaService()
api_params = service.prepare_for_send(message)

# 发送
# await bot.send_photo(**api_params)
```

### 3. 创建带按钮的消息

```python
# 使用内联键盘（Inline Keyboard）
message = (MessageBuilder()
    .text("请选择一个选项：")
    .inline_keyboard()
    .button("选项 1", callback_data="option_1")
    .button("选项 2", callback_data="option_2")
    .row()
    .button("取消", callback_data="cancel")
    .build()
    .build())

# 准备发送
service = TelegramMediaService()
api_params = service.prepare_for_send(message)

# 发送
# await bot.send_message(**api_params)
```

### 4. 创建回复键盘（Reply Keyboard）

```python
# 使用回复键盘
message = (MessageBuilder()
    .text("请选择操作：")
    .reply_keyboard()
    .button("开始")
    .button("设置")
    .row()
    .button("帮助")
    .resize(True)
    .one_time(True)
    .build()
    .build())

# 准备发送
service = TelegramMediaService()
api_params = service.prepare_for_send(message)

# 发送
# await bot.send_message(**api_params)
```

## 核心概念

### 媒体类型（MediaAttachment）

支持所有 Telegram 媒体类型：

```python
from src.autoresearch.core.services.telegram_media import (
    MediaAttachment, MediaType
)

# 图片
photo = MediaAttachment(
    media_type=MediaType.PHOTO,
    file_path="/path/to/photo.jpg",
    caption="测试图片",
    width=1920,
    height=1080
)

# 视频
video = MediaAttachment(
    media_type=MediaType.VIDEO,
    file_path="/path/to/video.mp4",
    duration=300,  # 5 分钟
    width=1920,
    height=1080,
    caption="测试视频"
)

# 音频
audio = MediaAttachment(
    media_type=MediaType.AUDIO,
    file_path="/path/to/audio.mp3",
    duration=180,  # 3 分钟
    caption="测试音频"
)

# 文档
document = MediaAttachment(
    media_type=MediaType.DOCUMENT,
    file_path="/path/to/document.pdf",
    filename="document.pdf",
    mime_type="application/pdf",
    caption="测试文档"
)
```

### 键盘类型

#### 内联键盘（InlineKeyboardMarkup）

```python
from src.autoresearch.core.services.telegram_media import (
    InlineKeyboardMarkup, InlineKeyboardButton
)

keyboard = InlineKeyboardMarkup()
keyboard.add_button(InlineKeyboardButton(
    text="访问网站",
    url="https://example.com"
))
keyboard.add_button(InlineKeyboardButton(
    text="执行操作",
    callback_data="action_1"
), row=1)  # 添加到第二行
```

#### 回复键盘（ReplyKeyboardMarkup）

```python
from src.autoresearch.core.services.telegram_media import (
    ReplyKeyboardMarkup, ReplyKeyboardButton
)

keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,  # 调整键盘大小
    one_time_keyboard=True  # 一次性键盘
)
keyboard.add_button(ReplyKeyboardButton(text="开始"))
keyboard.add_row([
    ReplyKeyboardButton(text="选项1"),
    ReplyKeyboardButton(text="选项2")
])
```

### 富消息（RichMessage）

`RichMessage` 是核心数据模型，封装了文本、媒体和交互元素：

```python
from src.autoresearch.core.services.telegram_media import RichMessage

message = RichMessage(
    text="测试消息",
    parse_mode="Markdown",
    disable_web_page_preview=True,
    media=photo,  # MediaAttachment 对象
    reply_markup=keyboard  # 键盘对象
)

# 验证消息
if message.validate():
    # 转换为 Telegram API 参数
    api_params = message.to_telegram_api()
```

## 序列化与持久化

### 序列化消息

```python
service = TelegramMediaService()

# 序列化为 JSON
json_str = service.serialize_message(message)

# 保存到数据库/文件
# with open("message.json", "w") as f:
#     f.write(json_str)
```

### 反序列化消息

```python
# 从 JSON 恢复
restored_message = service.deserialize_message(json_str)

# 验证恢复的消息
assert restored_message.text == message.text
```

## 降级机制

当消息包含不支持的内容时，服务会自动降级：

```python
# 创建无效消息（媒体没有来源）
invalid_media = MediaAttachment(media_type=MediaType.PHOTO)
invalid_message = RichMessage(media=invalid_media)

# 自动降级为纯文本
service = TelegramMediaService(auto_downgrade=True)
api_params = service.prepare_for_send(invalid_message)

# 降级后的消息会包含媒体描述
assert "图片" in api_params["text"]
```

## 便捷函数

```python
from src.autoresearch.core.services.telegram_media import (
    text_message, photo_message, document_message,
    with_inline_keyboard, with_reply_keyboard, remove_keyboard
)

# 创建文本消息
msg1 = text_message("Hello", parse_mode="Markdown")

# 创建图片消息
msg2 = photo_message(file_path="/path/to/photo.jpg", caption="测试")

# 创建文档消息
msg3 = document_message(
    file_path="/path/to/doc.pdf",
    filename="doc.pdf",
    caption="文档说明"
)

# 为消息添加内联键盘
msg4 = with_inline_keyboard(msg1, [
    [{"text": "按钮1", "callback_data": "btn1"}],
    [{"text": "按钮2", "callback_data": "btn2"}]
])

# 为消息添加回复键盘
msg5 = with_reply_keyboard(msg1, [
    ["选项1", "选项2"],
    ["取消"]
], resize=True)

# 移除回复键盘
msg6 = remove_keyboard(msg1)
```

## 与 Router 集成

### 方式 1：直接使用服务类

```python
# src/autoresearch/api/routers/gateway_telegram.py
from src.autoresearch.core.services import TelegramMediaService

class TelegramGateway:
    def __init__(self):
        self.media_service = TelegramMediaService()

    async def send_rich_message(self, chat_id: int, message_data: dict):
        """发送富消息"""
        # 从字典创建消息
        message = self.media_service.create_message(message_data)

        # 准备发送参数
        api_params = self.media_service.prepare_for_send(message)

        # 添加 chat_id
        api_params["chat_id"] = chat_id

        # 发送消息
        if "path" in api_params:
            # 媒体消息
            await self.bot.send_photo(**api_params)
        else:
            # 文本消息
            await self.bot.send_message(**api_params)
```

### 方式 2：使用序列化数据

```python
# 从数据库恢复消息
async def send_saved_message(self, chat_id: int, message_json: str):
    # 反序列化
    service = TelegramMediaService()
    message = service.deserialize_message(message_json)

    # 准备发送
    api_params = service.prepare_for_send(message)
    api_params["chat_id"] = chat_id

    # 发送
    await self.bot.send_message(**api_params)
```

## 数据模型

### MediaType（媒体类型）

```python
class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    ANIMATION = "animation"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"
```

### ParseMode（解析模式）

```python
class ParseMode(str, Enum):
    MARKDOWN = "Markdown"
    MARKDOWN_V2 = "MarkdownV2"
    HTML = "HTML"
    PLAIN = "None"
```

### RichMessage 字段

```python
@dataclass
class RichMessage:
    text: Optional[str] = None
    parse_mode: Optional[ParseMode] = ParseMode.PLAIN
    disable_web_page_preview: bool = False
    disable_notification: bool = False
    media: Optional[MediaAttachment] = None
    reply_markup: Optional[Markup] = None
    reply_to_message_id: Optional[int] = None
```

## 测试

运行完整测试套件：

```bash
# 使用 pytest
pytest tests/test_telegram_media.py -v

# 或直接运行
python3 tests/test_telegram_media.py
```

测试覆盖：
- ✅ 所有媒体类型
- ✅ 所有交互元素
- ✅ 序列化/反序列化
- ✅ 消息构建器
- ✅ 降级机制
- ✅ 完整工作流程

## API 参考

### TelegramMediaService

```python
class TelegramMediaService:
    def __init__(self, auto_downgrade: bool = True):
        """初始化服务

        Args:
            auto_downgrade: 是否自动降级无效消息
        """

    def create_message(self, message_data: Dict) -> RichMessage:
        """从字典创建消息"""

    def prepare_for_send(self, message: RichMessage) -> Dict:
        """准备消息用于发送"""

    def serialize_message(self, message: RichMessage) -> str:
        """序列化消息为 JSON"""

    def deserialize_message(self, json_str: str) -> RichMessage:
        """从 JSON 反序列化消息"""

    def builder(self) -> MessageBuilder:
        """创建消息构建器"""
```

### MessageBuilder

```python
class MessageBuilder:
    def text(self, text: str) -> MessageBuilder:
        """设置文本"""

    def parse_mode(self, mode: Union[ParseMode, str]) -> MessageBuilder:
        """设置解析模式"""

    def photo(self, ...) -> MessageBuilder:
        """添加图片"""

    def document(self, ...) -> MessageBuilder:
        """添加文档"""

    def inline_keyboard(self) -> InlineKeyboardBuilder:
        """创建内联键盘"""

    def reply_keyboard(self) -> ReplyKeyboardBuilder:
        """创建回复键盘"""

    def disable_web_page_preview(self, disable: bool) -> MessageBuilder:
        """禁用网页预览"""

    def disable_notification(self, disable: bool) -> MessageBuilder:
        """禁用通知"""

    def reply_to(self, message_id: int) -> MessageBuilder:
        """回复到指定消息"""

    def build(self) -> RichMessage:
        """构建消息"""
```

## 最佳实践

### 1. 始终验证消息

```python
message = MessageBuilder().text("测试").build()

if not message.validate():
    # 处理无效消息
    message = message.downgrade()
```

### 2. 使用服务类管理序列化

```python
service = TelegramMediaService()

# 推荐：使用服务类
json_str = service.serialize_message(message)
restored = service.deserialize_message(json_str)

# 不推荐：直接手动序列化
# json_str = json.dumps(message.serialize())
```

### 3. 利用构建器的链式调用

```python
# 推荐
message = (MessageBuilder()
    .text("测试")
    .parse_mode("Markdown")
    .inline_keyboard()
    .button("按钮1", callback_data="btn1")
    .build()
    .build())

# 不推荐
message = RichMessage()
message.text = "测试"
message.parse_mode = ParseMode.MARKDOWN
# ...
```

### 4. 启用自动降级

```python
# 生产环境推荐启用
service = TelegramMediaService(auto_downgrade=True)
```

## 常见问题

### Q: 如何发送本地文件？

```python
message = (MessageBuilder()
    .photo(file_path="/path/to/photo.jpg")
    .build())
```

### Q: 如何发送 URL？

```python
message = (MessageBuilder()
    .photo(file_url="https://example.com/photo.jpg")
    .build())
```

### Q: 如何使用 file_id？

```python
message = (MessageBuilder()
    .photo(file_id="AgADbQExG8kxEg...")
    .build())
```

### Q: 如何发送二进制数据？

```python
with open("photo.jpg", "rb") as f:
    data = f.read()

message = (MessageBuilder()
    .photo(file_data=data)
    .build())
```

### Q: 如何移除键盘？

```python
from src.autoresearch.core.services.telegram_media import remove_keyboard

message = remove_keyboard(text_message("键盘已移除"))
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0 (2026-03-26)

- ✅ 初始版本
- ✅ 支持所有媒体类型
- ✅ 支持所有交互元素
- ✅ 完整的序列化/反序列化
- ✅ 自动降级机制
- ✅ 流式构建器 API
- ✅ 完整的测试覆盖
