# 🔴 待办：玛露内部营销群魔法链接安全共享

> **创建时间**：2026-03-26 04:21 GMT+8
> **优先级**：高
> **工作分支**：codex/continue-autonomous-agent-stack
> **负责人**：C5/C6 (Channel组) + S1 (Security组)

---

## 🎯 目标

实现魔法链接在白名单群组内的安全共享，彻底杜绝链接外泄风险。

---

## 📋 核心任务

### 1. 环境变量与群组白名单加载 ⏳

**文件**：`models.py` 或配置加载模块

**任务**：
- ✅ 新增 `AUTORESEARCH_INTERNAL_GROUPS` 环境变量
- ✅ 支持解析多个群组ID列表（如 `[-10012345678, -10098765432]`）
- ✅ 验证群组ID格式（必须是负数）

**示例代码**：
```python
import os
from typing import List

def load_internal_groups() -> List[int]:
    """加载内部群组白名单"""
    groups_str = os.getenv("AUTORESEARCH_INTERNAL_GROUPS", "")
    if not groups_str:
        return []
    
    try:
        groups = eval(groups_str)  # 注意：生产环境应使用json.loads
        # 验证格式
        if not isinstance(groups, list):
            raise ValueError("必须是列表")
        if not all(isinstance(g, int) and g < 0 for g in groups):
            raise ValueError("群组ID必须是负数")
        return groups
    except Exception as e:
        print(f"⚠️ 加载内部群组失败: {e}")
        return []
```

---

### 2. 智能路由与JWT签发逻辑更新 ⏳

**文件**：`gateway_telegram.py`

**任务**：
- ✅ 监听 `/status` 指令，判断 `message.chat.id`
- ✅ **白名单群内**：
  - 直接回复包含魔法链接的内联按钮（Inline Button）
  - JWT Payload 包含 `{"scope": "group", "chat_id": message.chat.id}`
- ✅ **普通群**：
  - 维持原有的"私聊回传路由 (DM Routing)"安全策略

**示例代码**：
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import jwt
from datetime import datetime, timedelta

async def handle_status_command(update, context):
    """处理 /status 指令"""
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    
    # 加载白名单
    internal_groups = load_internal_groups()
    
    if chat_id in internal_groups:
        # 白名单群：直接在群内回复
        token = jwt.encode({
            "user_id": user_id,
            "chat_id": chat_id,
            "scope": "group",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }, SECRET_KEY, algorithm="HS256")
        
        magic_link = f"https://your-domain.com/panel?token={token}"
        
        keyboard = [[InlineKeyboardButton("📊 查看工作看板", url=magic_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✅ 您的专属工作看板已就绪",
            reply_markup=reply_markup
        )
    else:
        # 普通群：私聊回传
        await update.message.reply_text(
            "📩 魔法链接已发送到您的私聊"
        )
        # 发送私聊消息...
```

---

### 3. 面板拦截器实时查岗机制 ⏳

**文件**：`panel_access.py`

**任务**：
- ✅ 解析TWA传来的访客UID和JWT中的chat_id
- ✅ 异步调用 `getChatMember(chat_id, user_id)`
- ✅ **放行条件**：member/administrator/creator
- ✅ **拒绝条件**：left/kicked/异常 → 403 + 审计日志
- ✅ **缓存**：5分钟TTL缓存（避免API限流）

**示例代码**：
```python
from functools import lru_cache
from datetime import datetime, timedelta
import asyncio

# 5分钟TTL缓存
@lru_cache(maxsize=1000)
def get_cached_membership(chat_id: int, user_id: int, cache_time: str) -> bool:
    """缓存群成员身份验证结果"""
    # cache_time 用于实现TTL
    pass

async def verify_group_membership(chat_id: int, user_id: int, bot) -> bool:
    """验证用户是否是群成员"""
    # 检查缓存
    cache_time = datetime.now().strftime("%Y%m%d%H%M")  # 分钟级缓存
    cache_key = f"{chat_id}:{user_id}:{cache_time}"
    
    # 调用Telegram API
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        
        # 放行条件
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            # 记录审计日志
            await log_unauthorized_access(chat_id, user_id, member.status)
            return False
    except Exception as e:
        # 异常情况拒绝访问
        await log_unauthorized_access(chat_id, user_id, f"error: {e}")
        return False

async def panel_access_interceptor(token: str, user_id: int, bot):
    """面板访问拦截器"""
    try:
        # 解析JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        # 验证scope
        if payload.get("scope") != "group":
            # 非群组scope，走其他验证逻辑
            return True
        
        chat_id = payload.get("chat_id")
        
        # 实时查岗
        is_member = await verify_group_membership(chat_id, user_id, bot)
        
        if is_member:
            return True
        else:
            raise HTTPException(status_code=403, detail="越权访问")
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

async def log_unauthorized_access(chat_id: int, user_id: int, reason: str):
    """记录越权访问尝试"""
    # 写入SQLite审计日志
    pass
```

---

## ✅ 验收标准

### 功能验收
- ✅ 群内成员点击魔法链接可直接访问
- ✅ 外部人员转发链接访问被拒绝（403）
- ✅ 审计日志记录所有越权访问尝试
- ✅ API调用缓存命中率 > 80%

### 安全验收
- ✅ JWT包含scope和chat_id
- ✅ 实时验证群成员身份（非缓存）
- ✅ 异常情况默认拒绝
- ✅ 审计日志完整（时间、用户、群组、原因）

### 性能验收
- ✅ API调用次数 < 10次/分钟（缓存生效）
- ✅ 响应时间 < 500ms
- ✅ 缓存命中率 > 80%

---

## 🛠️ 技术栈

- **Telegram Bot API**：getChatMember
- **JWT**：scope + chat_id
- **TTL Cache**：5分钟缓存
- **SQLite**：审计日志存储

---

## 📊 实现计划

| 阶段 | 任务 | 预计时间 | 负责人 |
|------|------|---------|--------|
| **Phase 1** | 环境变量配置 | 30分钟 | C5 |
| **Phase 2** | 智能路由逻辑 | 1小时 | C5/C6 |
| **Phase 3** | 面板拦截器 | 1小时 | S1 |
| **Phase 4** | 测试验证 | 30分钟 | QA |
| **总计** | - | **3小时** | - |

---

## 🚨 风险点

1. **Telegram API限流**：
   - 缓解：5分钟TTL缓存
   - 监控：API调用次数告警

2. **JWT泄露**：
   - 缓解：24小时过期
   - 监控：异常访问检测

3. **群成员状态变更**：
   - 缓解：实时验证（非长期缓存）
   - 监控：审计日志分析

---

## 📝 测试用例

### 测试场景1：白名单群内访问
```python
async def test_whitelist_group_access():
    """测试白名单群内访问"""
    # 1. 在白名单群内发送 /status
    # 2. 验证收到内联按钮
    # 3. 点击按钮，验证可以访问看板
    pass
```

### 测试场景2：外部人员转发链接
```python
async def test_external_user_blocked():
    """测试外部人员转发链接被拒绝"""
    # 1. 获取群内魔法链接
    # 2. 外部用户使用该链接
    # 3. 验证返回403
    # 4. 验证审计日志记录
    pass
```

### 测试场景3：用户被踢出群
```python
async def test_kicked_user_blocked():
    """测试被踢出群的用户被拒绝"""
    # 1. 用户在群内获取魔法链接
    # 2. 用户被踢出群
    # 3. 用户再次访问链接
    # 4. 验证返回403
    pass
```

---

## 📅 时间线

- **2026-03-26 04:21**：任务创建
- **预计完成**：2026-03-26 07:00（3小时）
- **验收时间**：2026-03-26 08:00

---

## 🔗 相关链接

- **仓库**：https://github.com/srxly888-creator/autonomous-agent-stack
- **分支**：codex/continue-autonomous-agent-stack
- **相关文档**：
  - `docs/TELEGRAM_SECURITY.md`
  - `docs/JWT_AUTHENTICATION.md`

---

**状态**：⏳ 待实现
**优先级**：🔴 高
**预计时间**：3小时
