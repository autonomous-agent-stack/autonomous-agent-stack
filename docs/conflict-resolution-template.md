# route_table.py 冲突修复模板

> 当 git merge 遇到冲突时，使用此模板解决

---

## 🔍 冲突检测点

### 可能冲突的文件

1. **`src/gateway/route_table.py`**
   - 冲突原因：main 分支可能已有旧版本
   - 解决方案：使用新版本（feature 分支）

2. **`src/security/apple_double_cleaner.py`**
   - 冲突原因：Agent-1 和 Agent-4 都创建了此文件
   - 解决方案：使用 Agent-4 的版本（更完整）

---

## 🛠️ 冲突修复步骤

### Step 1：查看冲突文件

```bash
git status
# 查看哪些文件有冲突
```

### Step 2：解决 route_table.py 冲突

**如果遇到冲突，使用以下内容替换**：

```python
"""
Topic Routing Table - 物理 ID 映射定义
基于 Telegram Forum Mode (Topics) 实现精准分流
"""

import os
from typing import Dict, Optional, Any

# 玛露执行车间主群组 ID
CHAT_ID = os.getenv("AUTORESEARCH_TG_CHAT_ID", "-1003896889449")

class TopicMap:
    """话题物理 ID 定义"""
    GENERAL = 1          # #General - 原话存档
    CONTENT_LAB = 2      # #内容实验室 - 图片分析
    SECURITY_AUDIT = 3   # #系统审计 - 安全日志
    MARKET_INTEL = 4     # #市场情报 - 趋势监控

# 业务类型到话题 ID 的映射契约
ROUTE_MAP: Dict[str, Optional[int]] = {
    "intelligence": TopicMap.MARKET_INTEL,    # 市场情报
    "content": TopicMap.CONTENT_LAB,           # 内容实验室
    "security": TopicMap.SECURITY_AUDIT,       # 系统审计
    "system": TopicMap.SECURITY_AUDIT,         # 系统审计
    "user_input": TopicMap.GENERAL,            # 原话存档
}

def get_routing_params(category: str) -> Dict[str, Any]:
    """
    根据业务类别获取 Telegram 发送参数

    Args:
        category: 业务类型（intelligence/content/security/system/user_input）

    Returns:
        {
            "chat_id": "-1003896889449",
            "message_thread_id": 2
        }
    """
    thread_id = ROUTE_MAP.get(category.lower(), TopicMap.GENERAL)
    return {
        "chat_id": CHAT_ID,
        "message_thread_id": thread_id
    }

# 示例：
# params = get_routing_params("content")
# -> {'chat_id': '-1003896889449', 'message_thread_id': 2}
```

**操作命令**：
```bash
# 方法 1：直接使用 feature 分支版本
git checkout --theirs src/gateway/route_table.py

# 方法 2：手动编辑
nano src/gateway/route_table.py
# 复制上面的内容，保存后继续
```

---

### Step 3：解决 apple_double_cleaner.py 冲突

**如果 Agent-1 和 Agent-4 都创建了此文件**：

```bash
# 使用 Agent-4 的版本（更完整，包含审计日志）
git checkout --theirs src/security/apple_double_cleaner.py
```

---

### Step 4：标记冲突已解决

```bash
# 添加已解决的文件
git add src/gateway/route_table.py
git add src/security/apple_double_cleaner.py

# 继续合并
git commit -m "merge: 解决 route_table.py 和 apple_double_cleaner.py 冲突"
```

---

## 🔍 验证修复

### 检查路由映射

```bash
# 运行测试
pytest tests/test_route_table.py -v

# 或手动验证
python3 -c "
from src.gateway.route_table import get_routing_params
print(get_routing_params('content'))
# 应输出：{'chat_id': '-1003896889449', 'message_thread_id': 2}
"
```

---

## 📊 冲突优先级

| 文件 | 优先级 | 解决方案 |
|------|--------|---------|
| `route_table.py` | 🔴 高 | 使用 feature 分支版本（物理ID已锁定） |
| `apple_double_cleaner.py` | 🟡 中 | 使用 Agent-4 版本（更完整） |
| 其他文件 | 🟢 低 | 逐个检查，优先使用 feature 分支 |

---

## 🚨 常见问题

### Q1：合并时提示 "CONFLICT (content): Merge conflict in src/gateway/route_table.py"

**A**：使用以下命令解决：
```bash
# 查看冲突
git diff src/gateway/route_table.py

# 使用 feature 分支版本
git checkout --theirs src/gateway/route_table.py
git add src/gateway/route_table.py
```

---

### Q2：合并后测试失败

**A**：检查环境变量是否正确：
```bash
# 确认 .env 文件存在
ls -la .env

# 确认配置正确
grep "AUTORESEARCH_TG_CHAT_ID" .env
# 应输出：AUTORESEARCH_TG_CHAT_ID="-1003896889449"
```

---

### Q3：Docker 容器启动失败

**A**：检查端口占用：
```bash
# 检查 8000 端口
lsof -i :8000

# 杀掉占用进程
kill -9 <PID>
```

---

## 📝 冲突解决检查清单

- [ ] 查看冲突文件列表
- [ ] 解决 `route_table.py` 冲突
- [ ] 解决 `apple_double_cleaner.py` 冲突
- [ ] 标记所有冲突已解决（`git add`）
- [ ] 运行测试验证（`pytest tests/ -v`）
- [ ] 提交合并（`git commit`）

---

**创建时间**：2026-03-26 09:50
**用途**：合并 feature/topic-routing-gateway 时的冲突修复参考
