# Super Agent Dashboard

> **监控面板** - 实时展示系统状态

---

## 📊 功能

### 1. 物理防御层

- **AppleDouble 清理次数**：实时统计
- **AST 拦截次数**：安全审计统计
- **宿主机状态**：M1 Pro / Tailscale
- **沙盒环境**：Docker 隔离

---

### 2. 智能体算力矩阵

| Agent | 状态 | 职责 |
|-------|------|------|
| 架构领航员 | idle | 系统架构设计 |
| 市场情报官 | working | 抓取 XHS 趋势 |
| 内容视觉专家 | idle | 多模态数据分析 |
| 安全审计员 | monitoring | 监控文件系统 |

---

### 3. MASFactory 编排拓扑

```
Input → PLANNER → MATRIX
```

- **4 Nodes**：Planner, Generator, Executor, Evaluator
- **3 Channels**：Control, Data, Feedback

---

### 4. 实时审计流

- [环境防御] 物理清理了 12 个 ._ 缓存文件
- [Bridge] 接收到来自 OpenClaw 的任务委派
- [AST] 拦截了一个未授权的 os.system 调用

---

## 🚀 使用方法

### 安装依赖

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack/panel
npm install lucide-react
```

### 启动开发服务器

```bash
npm run dev
# 访问 http://localhost:3000
```

---

## 📁 文件结构

```
panel/
├── components/
│   └── SuperAgentDashboard.tsx
├── pages/
│   └── index.tsx
└── package.json
```

---

## 🔧 集成到 FastAPI

### 创建静态文件路由

```python
# src/autoresearch/api/main.py

from fastapi.staticfiles import StaticFiles

app.mount("/panel", StaticFiles(directory="panel/out", html=True), name="panel")
```

### 访问面板

```
http://127.0.0.1:8001/panel
```

---

## 🎨 设计特点

- **浅色主题**：背景 `#ffffff` + `#f8f9fa`
- **极简风格**：无冗余装饰
- **响应式布局**：支持桌面和移动端
- **实时更新**：动态数据展示

---

**创建时间**：2026-03-26 10:07 GMT+8
**状态**：组件已创建
