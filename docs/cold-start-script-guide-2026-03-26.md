# ✅ 一键冷启动脚本使用说明

> **创建时间**：2026-03-26 10:45 GMT+8
> **状态**：⏳ 待修复导入问题

---

## ⚠️ 当前问题

**错误**：`ImportError: cannot import name 'health_router' from 'bridge'`

**原因**：
1. `bridge/__init__.py` 导出的是 `system_router`，但 `main.py` 尝试导入 `health_router`
2. `main.py` 中 logger 定义位置错误

---

## 🔧 修复方案

### 方案 A：统一命名（推荐）

```python
# src/bridge/__init__.py
from .router import router as system_router  # 统一使用 system_router
from .unified_router import router as blitz_router

# src/autoresearch/api/main.py
from bridge import system_router, blitz_router
app.include_router(system_router, tags=["bridge"])
app.include_router(blitz_router, tags=["blitz"])
```

---

### 方案 B：修改导出名称

```python
# src/bridge/__init__.py
from .router import router as health_router  # 改为 health_router
from .unified_router import router as blitz_router

# src/autoresearch/api/main.py
from bridge import health_router, blitz_router  # 使用 health_router
```

---

## 🚀 手动修复步骤

### 步骤 1：修复 bridge/__init__.py

```bash
cat > /Volumes/PS1008/Github/autonomous-agent-stack/src/bridge/__init__.py << 'EOF'
"""Bridge package - 系统健康状态 + Blitz Router"""

from __future__ import annotations

from .router import router as system_router
from .unified_router import router as blitz_router

__all__ = ["system_router", "blitz_router"]
EOF
```

---

### 步骤 2：修复 main.py

```bash
# 在 main.py 开头添加 logging（如果还没有）
sed -i '' '1a\
import logging\
logger = logging.getLogger(__name__)
' /Volumes/PS1008/Github/autonomous-agent-stack/src/autoresearch/api/main.py

# 删除重复的 logging 导入
sed -i '' '/^import logging$/d' /Volumes/PS1008/Github/autonomous-agent-stack/src/autoresearch/api/main.py
sed -i '' '/^logger = logging.getLogger(__name__)$/d' /Volumes/PS1008/Github/autonomous-agent-stack/src/autoresearch/api/main.py

# 再次在开头添加（确保只添加一次）
sed -i '' '1a\
import logging\
logger = logging.getLogger(__name__)
' /Volumes/PS1008/Github/autonomous-agent-stack/src/autoresearch/api/main.py
```

---

### 步骤 3：运行冷启动脚本

```bash
bash /Volumes/PS1008/Github/autonomous-agent-stack/scripts/cold-start.sh
```

---

## 📁 脚本位置

**脚本路径**：`/Volumes/PS1008/Github/autonomous-agent-stack/scripts/cold-start.sh`

**功能**：
- ✅ 清理端口（8001）
- ✅ 清理 AppleDouble 文件
- ✅ 启动 FastAPI 服务
- ✅ 健康检查（3 个端点）
- ✅ 显示 Agent 矩阵状态

---

## 🎯 预期结果

```
========================================
Super Agent Stack - 冷启动序列
========================================

[1/5] 清理残留进程...
  ✅ 端口 8001 空闲
[2/5] 物理环境防御（AppleDouble 清理）...
  ✅ 环境清理完成
[3/5] 启动 FastAPI 服务...
  服务 PID: 12345
[4/5] 健康检查...
  ✅ 主服务健康
  ✅ 系统健康 API
  ✅ Blitz API
[5/5] 系统状态...

========================================
✅ 启动成功！
========================================

服务地址：
  - 主服务:     http://127.0.0.1:8001
  - 文档:       http://127.0.0.1:8001/docs
  - 系统健康:   http://127.0.0.1:8001/api/v1/system/health
  - Blitz 状态: http://127.0.0.1:8001/api/v1/blitz/status

准备就绪，等待指令！
========================================
```

---

**创建时间**：2026-03-26 10:45 GMT+8
**状态**：⏳ 待手动修复导入问题
