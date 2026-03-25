# 全能管家生态接入 - 快速启动指南

> **5 分钟快速启动**

---

## 📋 前置要求

1. ✅ Python 3.10+
2. ✅ Google Cloud 项目（已启用 Calendar, Tasks, Drive API）
3. ✅ macOS 宿主机（用于 Apple Bridge）

---

## 🚀 步骤 1: 配置环境变量

```bash
# 复制环境变量模板
cp .env.omni-assistant.example .env

# 编辑 .env 文件
nano .env
```

**必填项**:
```bash
# Google OAuth 2.0
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost

# Apple Bridge
APPLE_BRIDGE_HOST=127.0.0.1
APPLE_BRIDGE_PORT=8765

# HITL Approval
HITL_APPROVAL_TIMEOUT=300
TELEGRAM_TWA_URL=http://localhost:8001/panel
```

---

## 🔑 步骤 2: 获取 Google OAuth 凭证

1. 访问 [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. 创建 OAuth 2.0 客户端 ID
3. 授权重定向 URI: `http://localhost`
4. 复制 Client ID 和 Client Secret 到 `.env`

**需要的 API**:
- Google Calendar API
- Google Tasks API
- Google Drive API

---

## 🌉 步骤 3: 启动 Apple Bridge（宿主机）

```bash
# 方式 1: 直接运行
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python -m src.integrations.apple_bridge.bridge

# 方式 2: 使用 uvicorn
uvicorn src.integrations.apple_bridge.bridge:app --host 0.0.0.0 --port 8765
```

**访问地址**:
- Bridge: http://127.0.0.1:8765
- Docs: http://127.0.0.1:8765/docs
- Health: http://127.0.0.1:8765/health

---

## ✅ 步骤 4: 验证安装

### 测试 Apple Bridge

```bash
# 健康检查
curl http://127.0.0.1:8765/health

# 添加提醒（需要授权）
curl -X POST http://127.0.0.1:8765/reminders/add \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试提醒",
    "notes": "这是一个测试提醒",
    "list_name": "Reminders"
  }'

# 列出提醒
curl http://127.0.0.1:8765/reminders/list
```

### 测试 Google Workspace

```python
from src.integrations.google_workspace import (
    GoogleCalendarClient,
    OAuthManager,
)

# 首次运行会打开浏览器进行 OAuth 授权
oauth = OAuthManager()
calendar = GoogleCalendarClient(oauth)

# 列出日程
events = calendar.list_google_events()
print(events)
```

---

## 🧪 步骤 5: 运行测试

```bash
# 运行所有集成测试
pytest tests/integrations/test_cross_ecosystem.py -v

# 运行特定测试
pytest tests/integrations/test_cross_ecosystem.py::TestMaluBusinessScenario -v
```

---

## 📊 业务场景示例

### 玛露业务场景

```python
from src.integrations.hitl_approval import ApprovalManager, ApprovalStatus
import asyncio

async def malu_business_scenario():
    approval_manager = ApprovalManager()

    # 1. 创建提醒审批请求
    reminder_request = approval_manager.create_reminder_approval(
        reminder_title="玛露遮瑕膏【挑战游泳级别持妆】测试计划",
        reminder_notes="验证游泳场景下的持妆效果，确保产品宣传真实性",
        due_date="2026-03-27",
    )

    # 2. 创建文件上传审批请求
    file_request = approval_manager.create_file_upload_approval(
        filename="malu_test_20260325.jpg",
        file_size=1024000,
        mime_type="image/jpeg",
        description="玛露遮瑕膏游泳测试图片",
    )

    # 3. 等待用户审批
    reminder_status = await approval_manager.wait_for_approval(reminder_request)
    file_status = await approval_manager.wait_for_approval(file_request)

    # 4. 根据审批结果执行操作
    if reminder_status == ApprovalStatus.APPROVED:
        # 调用 Apple Bridge 添加提醒
        pass

    if file_status == ApprovalStatus.APPROVED:
        # 调用 Google Drive API 上传文件
        pass

# 运行场景
asyncio.run(malu_business_scenario())
```

---

## 🔧 故障排查

### 问题 1: Google OAuth 授权失败

**解决方案**:
```bash
# 检查环境变量
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET

# 删除缓存的 token
rm ~/.config/autoresearch/google_token.json

# 重新授权
python -c "from src.integrations.google_workspace import OAuthManager; OAuthManager().get_credentials()"
```

### 问题 2: Apple Bridge 无法启动

**解决方案**:
```bash
# 检查端口是否被占用
lsof -i :8765

# 检查 Python 版本
python --version  # 需要 3.10+

# 检查依赖
pip install fastapi uvicorn pydantic
```

### 问题 3: AppleScript 执行失败

**解决方案**:
```bash
# 授权 Terminal/iTerm 访问 Reminders
# 系统偏好设置 → 安全性与隐私 → 隐私 → 自动化
# 勾选 Terminal/iTerm 的 Reminders 访问权限

# 测试 osascript
osascript -e 'tell application "Reminders" to get name of every list'
```

---

## 📚 下一步

1. ⏳ 配置 Telegram TWA Dashboard
2. ⏳ 集成 EventBus 通知
3. ⏳ 实现 SQLite 审计日志
4. ⏳ 完善测试覆盖率

---

## 🔗 相关链接

- **完整文档**: `docs/omni-assistant-integration.md`
- **实施报告**: `memory/omni-assistant-integration-2026-03-26.md`
- **Google API Console**: https://console.cloud.google.com/apis/credentials
- **FastAPI 文档**: https://fastapi.tiangolo.com/

---

**创建时间**: 2026-03-26 05:10 GMT+8
**状态**: ✅ 完成
