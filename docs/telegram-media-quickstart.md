# Telegram 媒体服务 - 快速开始

## 30 秒上手

```python
from src.autoresearch.core.services import TelegramMediaService, MessageBuilder

# 1. 初始化服务
service = TelegramMediaService()

# 2. 创建消息
message = (MessageBuilder()
    .text("请选择操作：")
    .inline_keyboard()
    .button("查看数据", callback_data="view_data")
    .button("设置", callback_data="settings")
    .build()
    .build())

# 3. 准备发送
api_params = service.prepare_for_send(message)

# 4. 发送
await bot.send_message(**api_params)
```

## 支持的功能

### 媒体类型
- ✅ 图片 (photo)
- ✅ 视频 (video)
- ✅ 音频 (audio)
- ✅ 文档 (document)
- ✅ 贴纸 (sticker)
- ✅ 动画 (animation)
- ✅ 语音 (voice)
- ✅ 圆形视频 (video_note)

### 交互元素
- ✅ 内联键盘 (inline keyboard)
- ✅ 回复键盘 (reply keyboard)
- ✅ Callback 按钮
- ✅ URL 按钮
- ✅ 请求联系人/位置

## 文件结构

```
src/autoresearch/core/services/
├── __init__.py
└── telegram_media.py          # 核心服务层 (29KB)

tests/
└── test_telegram_media.py     # 完整测试套件 (33KB)

docs/
├── telegram-media-service.md           # 用户文档
├── telegram-router-integration.md      # Router 集成文档
└── telegram-media-completion-report.md # 完成报告

examples/
└── telegram_media_example.py  # 10 个使用示例
```

## 快速链接

- 📖 [完整文档](docs/telegram-media-service.md)
- 🔌 [Router 集成](docs/telegram-router-integration.md)
- 📊 [完成报告](docs/telegram-media-completion-report.md)
- 💡 [使用示例](examples/telegram_media_example.py)

## 常见用法

### 发送文本消息

```python
from src.autoresearch.core.services import text_message, TelegramMediaService

service = TelegramMediaService()
msg = text_message("Hello, World!", "Markdown")
api_params = service.prepare_for_send(msg)
```

### 发送图片

```python
from src.autoresearch.core.services import photo_message

msg = photo_message(
    file_path="/path/to/photo.jpg",
    caption="测试图片"
)
api_params = service.prepare_for_send(msg)
```

### 发送带按钮的消息

```python
from src.autoresearch.core.services import (
    text_message, with_inline_keyboard, TelegramMediaService
)

service = TelegramMediaService()
msg = text_message("请选择：")
msg = with_inline_keyboard(msg, [
    [{"text": "选项1", "callback_data": "opt1"}],
    [{"text": "选项2", "callback_data": "opt2"}]
])
api_params = service.prepare_for_send(msg)
```

### 序列化和恢复

```python
service = TelegramMediaService()

# 序列化
json_str = service.serialize_message(message)

# 保存到数据库
# db.save(json_str)

# 恢复
restored = service.deserialize_message(json_str)
```

## 核心特性

- ✅ **类型安全** - 完整的类型注解
- ✅ **自动降级** - 不支持的内容自动降级
- ✅ **序列化友好** - 所有数据可序列化为 JSON
- ✅ **易于测试** - 独立的服务层
- ✅ **API 兼容** - 100% 兼容 Telegram Bot API

## 运行测试

```bash
# 方式 1：使用 pytest
pytest tests/test_telegram_media.py -v

# 方式 2：直接运行
python3 tests/test_telegram_media.py

# 方式 3：快速验证
python3 -c "
import sys
sys.path.insert(0, '.')
from src.autoresearch.core.services import *
service = TelegramMediaService()
msg = text_message('测试')
print('✓ 一切正常！')
"
```

## 运行示例

```bash
python3 examples/telegram_media_example.py
```

## 问题反馈

如有问题，请查看：
- [常见问题](docs/telegram-media-service.md#常见问题)
- [最佳实践](docs/telegram-media-service.md#最佳实践)
- [API 参考](docs/telegram-media-service.md#api-参考)

---

**创建时间：** 2026-03-26
**版本：** v1.0.0
**状态：** ✅ 完成并测试通过
