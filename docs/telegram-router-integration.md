# Telegram Router 集成接口文档

## 概述

本文档说明如何将 `telegram_media` 服务层集成到 Telegram Gateway Router 中。

**核心设计原则：**
- 🔌 **松耦合**：服务层完全独立，router 可直接消费
- 📦 **序列化优先**：所有数据可序列化为 JSON，便于传输和存储
- 🛡️ **容错设计**：自动降级，不会因不支持的内容而失败
- 🎯 **类型安全**：完整的类型注解，减少运行时错误

## 接口定义

### 1. 消息创建接口

#### 从字典创建消息

```python
from src.autoresearch.core.services import TelegramMediaService

service = TelegramMediaService()

# 从 API 格式创建
message = service.create_message({
    "text": "Hello, World!",
    "parse_mode": "Markdown",
    "reply_markup": {
        "inline_keyboard": [
            [{"text": "按钮", "callback_data": "btn"}]
        ]
    }
})
```

**支持的字典格式：**

1. **Telegram Bot API 原始格式**
   ```python
   {
       "text": "消息文本",
       "parse_mode": "Markdown",
       "disable_web_page_preview": True,
       "reply_markup": {
           "inline_keyboard": [[...]]
       }
   }
   ```

2. **序列化格式**
   ```python
   {
       "text": "消息文本",
       "parse_mode": "Markdown",
       "reply_markup_type": "inline",
       "reply_markup": {
           "inline_keyboard": [[...]]
       }
   }
   ```

### 2. 消息发送接口

#### 准备发送参数

```python
from src.autoresearch.core.services import TelegramMediaService

service = TelegramMediaService()
message = service.create_message(message_data)

# 准备发送参数（自动验证和降级）
api_params = service.prepare_for_send(message)

# api_params 是标准 Telegram Bot API 字典
# {
#     "text": "Hello, World!",
#     "parse_mode": "Markdown",
#     "reply_markup": {...}
# }
```

**返回值：**
- 类型：`Dict[str, Any]`
- 兼容：100% 兼容 Telegram Bot API
- 特性：自动清理 None 值

### 3. 序列化接口

#### 序列化消息

```python
service = TelegramMediaService()

# 序列化为 JSON 字符串
json_str = service.serialize_message(message)

# 用途：
# 1. 持久化到数据库
# 2. 通过网络传输
# 3. 日志记录
```

#### 反序列化消息

```python
# 从 JSON 恢复
restored = service.deserialize_message(json_str)

# 验证完整性
assert restored.text == message.text
```

## Router 集成示例

### 完整的 Router 实现

```python
# src/autoresearch/api/routers/gateway_telegram.py

from typing import Dict, Any, Optional
from telegram import Bot, Update
from telegram.ext import Dispatcher

from src.autoresearch.core.services import TelegramMediaService


class TelegramGateway:
    """Telegram Gateway - 与 Telegram Bot API 交互"""

    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.media_service = TelegramMediaService(auto_downgrade=True)

    async def send_message(
        self,
        chat_id: int,
        message_data: Dict[str, Any]
    ) -> Any:
        """发送消息（统一入口）

        Args:
            chat_id: Telegram 聊天 ID
            message_data: 消息数据（支持多种格式）

        Returns:
            Telegram API 返回的消息对象
        """
        # 1. 创建 RichMessage
        message = self.media_service.create_message(message_data)

        # 2. 准备发送参数
        api_params = self.media_service.prepare_for_send(message)
        api_params["chat_id"] = chat_id

        # 3. 根据类型选择发送方法
        if "path" in api_params or "url" in api_params or "file_id" in api_params:
            # 媒体消息
            if message.media and message.media.media_type.value == "photo":
                return await self.bot.send_photo(**api_params)
            elif message.media and message.media.media_type.value == "video":
                return await self.bot.send_video(**api_params)
            elif message.media and message.media.media_type.value == "document":
                return await self.bot.send_document(**api_params)
            elif message.media and message.media.media_type.value == "audio":
                return await self.bot.send_audio(**api_params)
            else:
                # 默认作为文档发送
                return await self.bot.send_document(**api_params)
        else:
            # 文本消息
            return await self.bot.send_message(**api_params)

    async def send_photo(
        self,
        chat_id: int,
        photo_path: Optional[str] = None,
        photo_url: Optional[str] = None,
        photo_file_id: Optional[str] = None,
        caption: Optional[str] = None,
        reply_markup: Optional[Dict] = None
    ) -> Any:
        """发送图片（便捷方法）

        Args:
            chat_id: Telegram 聊天 ID
            photo_path: 本地文件路径
            photo_url: 远程文件 URL
            photo_file_id: Telegram file_id
            caption: 图片说明
            reply_markup: 键盘标记

        Returns:
            Telegram API 返回的消息对象
        """
        # 使用服务层创建消息
        from src.autoresearch.core.services.telegram_media import MessageBuilder

        message = (MessageBuilder()
            .photo(
                file_path=photo_path,
                file_url=photo_url,
                file_id=photo_file_id,
                caption=caption
            )
            .build())

        # 添加键盘（如果有）
        if reply_markup:
            message = self.media_service.create_message({
                "media": message.media.serialize(),
                "reply_markup": reply_markup
            })

        # 发送
        return await self.send_message(chat_id, message.serialize())

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        message_data: Dict[str, Any]
    ) -> Any:
        """编辑消息

        Args:
            chat_id: Telegram 聊天 ID
            message_id: 要编辑的消息 ID
            message_data: 新的消息数据

        Returns:
            Telegram API 返回的消息对象
        """
        # 创建消息
        message = self.media_service.create_message(message_data)

        # 准备参数
        api_params = self.media_service.prepare_for_send(message)
        api_params["chat_id"] = chat_id
        api_params["message_id"] = message_id

        # 编辑消息
        return await self.bot.edit_message_text(**api_params)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> bool:
        """回答回调查询

        Args:
            callback_query_id: 回调查询 ID
            text: 显示的文本
            show_alert: 是否显示为弹窗

        Returns:
            是否成功
        """
        return await self.bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert
        )


# FastAPI Router 集成示例
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class TelegramMessageRequest(BaseModel):
    """Telegram 消息请求"""
    chat_id: int
    message: Dict[str, Any]  # RichMessage 序列化格式

router = APIRouter()

# 初始化 Gateway
gateway = TelegramGateway(token=os.getenv("TELEGRAM_BOT_TOKEN"))

@router.post("/telegram/send")
async def send_telegram_message(request: TelegramMessageRequest):
    """发送 Telegram 消息 API

    Request Body:
    {
        "chat_id": 123456789,
        "message": {
            "text": "Hello, World!",
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "按钮", "callback_data": "btn"}]
                ]
            }
        }
    }
    """
    try:
        result = await gateway.send_message(
            chat_id=request.chat_id,
            message_data=request.message
        )
        return {"success": True, "message_id": result.message_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/send-photo")
async def send_telegram_photo(
    chat_id: int,
    photo_path: str = None,
    photo_url: str = None,
    caption: str = None
):
    """发送图片 API"""
    try:
        result = await gateway.send_photo(
            chat_id=chat_id,
            photo_path=photo_path,
            photo_url=photo_url,
            caption=caption
        )
        return {"success": True, "message_id": result.message_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/edit")
async def edit_telegram_message(
    chat_id: int,
    message_id: int,
    message: Dict[str, Any]
):
    """编辑消息 API"""
    try:
        result = await gateway.edit_message(
            chat_id=chat_id,
            message_id=message_id,
            message_data=message
        )
        return {"success": True, "message_id": result.message_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 数据流设计

### 1. 发送消息流程

```
┌─────────────┐
│  Client/   │
│  External  │
└──────┬──────┘
       │ HTTP Request
       │ {chat_id, message_data}
       ▼
┌─────────────────────┐
│  TelegramGateway    │
│  - send_message()   │
└──────┬──────────────┘
       │ 1. create_message()
       ▼
┌─────────────────────┐
│ TelegramMediaService│
│ - create_message()  │
└──────┬──────────────┘
       │ RichMessage
       ▼
┌─────────────────────┐
│ TelegramMediaService│
│ - prepare_for_send()│
└──────┬──────────────┘
       │ API Params
       ▼
┌─────────────────────┐
│   Telegram Bot      │
│      API            │
└─────────────────────┘
```

### 2. 消息数据格式

#### 输入格式（灵活）

支持多种输入格式，router 可以接受：

1. **API 原始格式**（从 Telegram 接收）
   ```python
   {
       "message_id": 123,
       "from": {"id": 456, "username": "user"},
       "chat": {"id": 789},
       "text": "Hello",
       "photo": [...]
   }
   ```

2. **RichMessage 序列化格式**（从数据库恢复）
   ```python
   {
       "text": "Hello",
       "parse_mode": "Markdown",
       "media": {...},
       "reply_markup_type": "inline",
       "reply_markup": {...}
   }
   ```

3. **简化格式**（从用户输入）
   ```python
   {
       "text": "Hello",
       "buttons": [["Button1", "Button2"]]
   }
   ```

#### 输出格式（标准）

统一输出为 Telegram Bot API 兼容格式：

```python
{
    "chat_id": 123456789,
    "text": "Hello, World!",
    "parse_mode": "Markdown",
    "reply_markup": {
        "inline_keyboard": [[...]]
    }
}
```

## 错误处理

### 自动降级

```python
# 当消息无效时，自动降级
service = TelegramMediaService(auto_downgrade=True)

# 无效消息（媒体没有来源）
invalid_message = RichMessage(
    media=MediaAttachment(media_type=MediaType.PHOTO)
)

# 自动降级为纯文本
api_params = service.prepare_for_send(invalid_message)
# {
#     "text": "[媒体内容]\\n\\n[媒体类型: photo]",
#     "parse_mode": None
# }
```

### 手动降级

```python
if not message.validate():
    # 尝试降级
    downgraded = message.downgrade()
    if downgraded:
        message = downgraded
    else:
        raise ValueError("Invalid message")
```

## 测试接口

### 单元测试

```python
# tests/test_gateway_integration.py

import pytest
from src.autoresearch.api.routers.gateway_telegram import TelegramGateway
from src.autoresearch.core.services import TelegramMediaService

@pytest.fixture
def gateway():
    return TelegramGateway(token="test_token")

@pytest.fixture
def media_service():
    return TelegramMediaService()

def test_send_text_message(gateway, media_service):
    """测试发送文本消息"""
    message_data = {
        "text": "Test message",
        "parse_mode": "Markdown"
    }

    # Mock bot.send_message
    # ...

    # 实际测试
    # result = await gateway.send_message(123, message_data)
    # assert result.message_id is not None

def test_send_photo_message(gateway, media_service):
    """测试发送图片"""
    message_data = {
        "type": "photo",
        "file_path": "/test/photo.jpg",
        "caption": "Test photo"
    }

    # Mock bot.send_photo
    # ...

    # 实际测试
    # result = await gateway.send_photo(123, photo_path="/test/photo.jpg")
    # assert result.message_id is not None

def test_message_serialization(media_service):
    """测试消息序列化"""
    message = media_service.create_message({
        "text": "Test",
        "parse_mode": "Markdown"
    })

    # 序列化
    json_str = media_service.serialize_message(message)

    # 反序列化
    restored = media_service.deserialize_message(json_str)

    assert restored.text == message.text
    assert restored.parse_mode == message.parse_mode
```

## 性能优化

### 1. 批量发送

```python
async def send_bulk_messages(
    self,
    messages: List[Tuple[int, Dict[str, Any]]]
) -> List[Any]:
    """批量发送消息

    Args:
        messages: [(chat_id, message_data), ...]

    Returns:
        List[message_id]
    """
    tasks = [
        self.send_message(chat_id, message_data)
        for chat_id, message_data in messages
    ]

    return await asyncio.gather(*tasks)
```

### 2. 消息缓存

```python
from functools import lru_cache

class TelegramGateway:
    @lru_cache(maxsize=1000)
    def _prepare_message(self, message_json: str) -> Dict:
        """缓存消息准备结果"""
        message = self.media_service.deserialize_message(message_json)
        return self.media_service.prepare_for_send(message)
```

## 安全考虑

### 1. 文件路径验证

```python
def validate_file_path(file_path: str) -> bool:
    """验证文件路径安全性"""
    # 防止路径遍历攻击
    if ".." in file_path or file_path.startswith("/"):
        return False

    # 检查文件扩展名
    allowed_extensions = {".jpg", ".png", ".pdf", ".mp3"}
    if Path(file_path).suffix not in allowed_extensions:
        return False

    return True
```

### 2. Callback Data 验证

```python
def validate_callback_data(callback_data: str) -> bool:
    """验证 callback 数据"""
    # 限制长度（Telegram 限制为 64 字节）
    if len(callback_data.encode('utf-8')) > 64:
        return False

    # 防止注入攻击
    if any(char in callback_data for char in ['\n', '\r', '\t']):
        return False

    return True
```

## 监控和日志

### 结构化日志

```python
import logging

logger = logging.getLogger(__name__)

class TelegramGateway:
    async def send_message(self, chat_id: int, message_data: Dict):
        logger.info(
            "Sending message",
            extra={
                "chat_id": chat_id,
                "message_type": message_data.get("type", "text"),
                "has_media": "media" in message_data,
                "has_markup": "reply_markup" in message_data
            }
        )

        try:
            result = await self._send_message_impl(chat_id, message_data)
            logger.info("Message sent successfully", extra={
                "message_id": result.message_id
            })
            return result
        except Exception as e:
            logger.error("Failed to send message", extra={
                "error": str(e),
                "chat_id": chat_id
            })
            raise
```

## 总结

### 集成步骤

1. **初始化服务**
   ```python
   from src.autoresearch.core.services import TelegramMediaService

   media_service = TelegramMediaService(auto_downgrade=True)
   ```

2. **创建消息**
   ```python
   message = media_service.create_message(message_data)
   ```

3. **准备发送**
   ```python
   api_params = media_service.prepare_for_send(message)
   ```

4. **调用 API**
   ```python
   await bot.send_message(**api_params)
   ```

### 优势

- ✅ **类型安全**：完整的数据模型和类型注解
- ✅ **自动降级**：不会因不支持的内容而失败
- ✅ **序列化友好**：所有数据可序列化为 JSON
- ✅ **易于测试**：独立的服务层，易于 mock
- ✅ **灵活扩展**：支持自定义媒体类型和交互元素
- ✅ **API 兼容**：100% 兼容 Telegram Bot API
