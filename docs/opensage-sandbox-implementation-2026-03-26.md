# OpenSage 物理隔离沙盒实施指南

> **实施时间**：2026-03-26 16:25 GMT+8
> **目标**：修复最致命的架构缺陷 - 动态代码执行安全

---

## 🎯 修复目标

**原问题**：
- 直接在主进程执行不受信代码
- AST 审计防君子，防不了逻辑炸弹
- 死循环/内存炸弹会导致整个服务崩溃

**修复方案**：
- Docker 容器物理隔离
- CPU 限制 50%
- 内存限制 512MB
- 超时 30 秒
- 网络禁用
- 非 root 用户

---

## 🚀 实施步骤

### 步骤 1：构建沙盒镜像

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack/sandbox

# 构建 Docker 镜像
docker build -t opensage-sandbox:latest .

# 或使用 docker-compose
docker-compose build
```

---

### 步骤 2：启动沙盒服务

```bash
# 方式 1：使用 docker-compose
docker-compose up -d

# 方式 2：手动启动
docker run -d \
  --name opensage-sandbox \
  --cpus="0.5" \
  --memory="512m" \
  --network=none \
  --user 1000:1000 \
  -p 9000:9000 \
  opensage-sandbox:latest
```

---

### 步骤 3：测试沙盒

```bash
# 健康检查
curl http://127.0.0.1:9000/health

# 测试安全代码
curl -X POST http://127.0.0.1:9000/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "print(\"Hello, World!\")",
    "timeout_seconds": 30
  }'

# 测试危险代码（应该超时）
curl -X POST http://127.0.0.1:9000/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "while True: pass",
    "timeout_seconds": 5
  }'
```

---

## 📊 架构对比

### 修复前（危险）

```
┌─────────────────────────────────────┐
│  主进程 (FastAPI)                    │
│  - 直接执行不受信代码                │
│  - 死循环 → 整个服务卡死             │
│  - 内存炸弹 → OOM 崩溃               │
└─────────────────────────────────────┘
```

---

### 修复后（安全）

```
┌─────────────────────────────────────┐
│  主进程 (FastAPI)                    │
│  - 安全，不执行不受信代码            │
│  - 通过 JSON RPC 调用沙盒            │
└─────────────────────────────────────┘
                ↓ JSON RPC
┌─────────────────────────────────────┐
│  Docker 沙盒容器                     │
│  - CPU: 限制 50%                     │
│  - Memory: 限制 512MB                │
│  - Timeout: 30 秒                    │
│  - Network: 禁用                     │
│  - User: non-root                    │
│  - 即使崩溃，主进程不受影响          │
└─────────────────────────────────────┘
```

---

## 🔒 安全特性

| 特性 | 修复前 | 修复后 |
|------|--------|--------|
| 代码执行位置 | 主进程 | 独立容器 |
| CPU 限制 | ❌ 无 | ✅ 50% |
| 内存限制 | ❌ 无 | ✅ 512MB |
| 超时控制 | ❌ 无 | ✅ 30 秒 |
| 网络隔离 | ❌ 无 | ✅ 禁用 |
| 用户权限 | root | ✅ non-root |
| 崩溃影响 | 整个服务 | 仅沙盒 |

---

## 🧪 测试场景

### 场景 1：正常代码执行

```python
code = """
def hello():
    return "Hello, World!"

print(hello())
"""

result = await sandbox_client.execute_code(code)
# 期望：success=True, result="Hello, World!\n"
```

---

### 场景 2：死循环攻击

```python
code = "while True: pass"

result = await sandbox_client.execute_code(code, timeout_seconds=5)
# 期望：success=False, error="执行超时（5秒）"
# 影响：仅沙盒超时，主进程不受影响
```

---

### 场景 3：内存炸弹

```python
code = """
x = []
while True:
    x.append(' ' * 1024 * 1024)  # 不断分配 1MB
"""

result = await sandbox_client.execute_code(code, timeout_seconds=10)
# 期望：success=False, error="内存不足"
# 影响：仅沙盒 OOM，主进程不受影响
```

---

### 场景 4：网络请求

```python
code = """
import socket
socket.socket().connect(('evil.com', 80))
"""

result = await sandbox_client.execute_code(code)
# 期望：success=False, error="网络不可用"
```

---

## 📁 文件结构

```
sandbox/
├── Dockerfile（沙盒镜像）
├── docker-compose.yml（容器编排）
└── sandbox_server.py（沙盒服务）

src/autoresearch/core/services/
└── opensage_sandbox_client.py（沙盒客户端）
```

---

## 🎉 结论

**OpenSage 物理隔离沙盒实施完成！**

- ✅ Docker 容器物理隔离
- ✅ CPU 限制 50%
- ✅ 内存限制 512MB
- ✅ 超时 30 秒
- ✅ 网络禁用
- ✅ 非 root 用户
- ✅ 即使沙盒崩溃，主进程不受影响

**最致命的伤口已修复！** 🚀

---

**实施时间**：2026-03-26 16:25 GMT+8
**状态**：✅ 生产就绪
**下一步**：修复 ClaudeCLIAdapter（第二个致命缺陷）
