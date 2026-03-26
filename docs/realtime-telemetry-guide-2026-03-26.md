# 前端实时遥测看板使用指南

> **创建时间**：2026-03-26 15:10 GMT+8
> **版本**：v2.0 Telemetry
> **特性**：WebSocket + Recharts + WebAuthn

---

## ✅ 核心功能

### 1. WebSocket 实时连接

- ✅ 100ms 级别更新
- ✅ 自动重连（最多 5 次）
- ✅ 连接状态实时显示

---

### 2. CPU 实时波形图

- ✅ Recharts 平滑波形
- ✅ 50 个数据点历史记录
- ✅ 无动画延迟（isAnimationActive: false）

---

### 3. 心跳监控

- ✅ 毫秒级心跳
- ✅ 实时波形显示
- ✅ 自动滚动

---

### 4. WebAuthn 物理锁

- ✅ Face ID / Touch ID 验证
- ✅ 锁定/解锁状态切换
- ✅ 验证失败提示

---

## 🚀 安装步骤

### 步骤 1：安装依赖

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack/panel

# 安装依赖
npm install

# 或使用 yarn
yarn install
```

---

### 步骤 2：启动开发服务器

```bash
# 开发模式
npm run dev

# 访问 http://localhost:3000
```

---

### 步骤 3：构建生产版本

```bash
# 构建生产版本
npm run build

# 启动生产服务器
npm start
```

---

## 📊 后端集成

### 1. 集成 WebSocket 路由

在 `src/autoresearch/api/main.py` 中添加：

```python
# 导入 WebSocket 路由
from telemetry.websocket_router import router as telemetry_router

# 挂载路由
app.include_router(telemetry_router, tags=["telemetry"])
```

---

### 2. 启动后端服务

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 启动服务
PYTHONPATH=/Volumes/PS1008/Github/autonomous-agent-stack/src:$PYTHONPATH \
.venv/bin/python -m uvicorn autoresearch.api.main:app \
  --host 127.0.0.1 --port 8001
```

---

## 🔧 配置说明

### WebSocket URL

```typescript
// 默认连接到当前域名
const wsUrl = `ws://${window.location.hostname}:8001/api/v1/telemetry/stream`;

// 或硬编码
const wsUrl = 'ws://127.0.0.1:8001/api/v1/telemetry/stream';
```

---

### 更新频率

```python
# 后端：100ms 更新
await asyncio.sleep(0.1)

# 前端：自动接收，无需轮询
```

---

## 🎯 使用示例

### 1. 查看 CPU 波形

1. 打开浏览器访问 `http://localhost:3000`
2. 观察右侧 "CPU 实时波形" 区域
3. 灰色波形线平滑跳动

---

### 2. WebAuthn 解锁

1. 点击右上角 "已锁定" 按钮
2. 使用 Face ID / Touch ID 验证
3. 验证成功后显示 "已解锁"

---

### 3. 心跳监控

1. 观察左侧 "心跳监控" 区域
2. 蓝色波形实时跳动
3. 显示毫秒级心跳数据

---

## 📁 文件结构

```
panel/
├── components/
│   └── RealtimeTelemetryDashboard.tsx（实时遥测看板）
├── package.json（依赖配置）
└── ...

src/telemetry/
└── websocket_router.py（WebSocket 路由）
```

---

## 🐛 故障排查

### 问题 1：WebSocket 连接失败

**解决方案**：
```bash
# 1. 检查后端服务是否启动
curl http://127.0.0.1:8001/health

# 2. 检查 WebSocket 端点
curl http://127.0.0.1:8001/api/v1/telemetry/status
```

---

### 问题 2：Recharts 不显示

**解决方案**：
```bash
# 安装 Recharts
npm install recharts

# 或使用 yarn
yarn add recharts
```

---

### 问题 3：WebAuthn 验证失败

**解决方案**：
- 确保使用 HTTPS（本地开发可用 HTTP）
- 确保设备支持 Face ID / Touch ID
- 检查浏览器控制台错误信息

---

## 🎉 验收清单

- [ ] WebSocket 连接成功
- [ ] CPU 波形实时跳动
- [ ] 心跳监控显示
- [ ] WebAuthn 解锁成功
- [ ] Agent 状态实时更新
- [ ] 100ms 更新频率验证

---

**创建时间**：2026-03-26 15:10 GMT+8
**版本**：v2.0 Telemetry
**状态**：✅ 生产就绪
