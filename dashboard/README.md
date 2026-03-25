# 🤖 Autonomous Agent Stack Dashboard

现代化的 Web Dashboard，用于实时展示 autonomous-agent-stack 项目状态、Agent 运行情况和测试结果。

![Dashboard Preview](./screenshots/preview.png)

## ✨ 特性

- **实时监控** - 每 30 秒自动刷新数据
- **响应式设计** - 完美适配移动端（Telegram 内置浏览器）
- **暗色主题** - 护眼设计，适合长时间查看
- **交互式图表** - 使用 Recharts 展示数据可视化
- **零配置部署** - 支持 Vercel 一键部署

## 🚀 快速开始

### 1. 安装依赖

```bash
cd dashboard
npm install
```

### 2. 本地开发

```bash
npm run dev
```

访问 http://localhost:3000

### 3. 生产构建

```bash
npm run build
npm start
```

## 📦 技术栈

- **框架**: Next.js 14 (App Router)
- **UI 库**: React 18
- **样式**: Tailwind CSS
- **图表**: Recharts
- **数据获取**: SWR
- **图标**: Lucide React
- **语言**: TypeScript

## 📄 页面结构

### 首页 (`/`)
- 项目概览卡片（完成度、成功率、运行时间）
- Agent 状态表格（10个Agent的实时状态）
- 最近提交列表

### 测试页 (`/tests`)
- 测试通过率图表（饼图）
- 测试用例列表（分类显示）
- 失败测试详情

### 对齐页 (`/parity`)
- OpenClaw 对齐度进度条
- P0/P1/P2 功能完成度
- 缺口功能清单

### Agent 页 (`/agents`)
- 10-Agent 协作矩阵可视化
- Agent 响应时间对比（柱状图）
- Agent 能力雷达图

## 🔌 API 端点

所有 API 端点返回 JSON 格式数据：

```
GET /api/status   - 项目整体状态
GET /api/agents   - Agent 列表和状态
GET /api/tests    - 测试结果
GET /api/parity   - 对齐度数据
GET /api/commits  - 最近提交
```

### 示例响应

#### `/api/status`

```json
{
  "projectName": "Autonomous Agent Stack",
  "overallProgress": 68,
  "successRate": 85.5,
  "uptime": "15d 8h 32m",
  "health": "healthy"
}
```

## 🚀 部署到 Vercel

### 方法一：通过 Vercel CLI

```bash
# 安装 Vercel CLI
npm i -g vercel

# 部署
vercel
```

### 方法二：通过 GitHub 集成

1. 将代码推送到 GitHub
2. 在 [Vercel](https://vercel.com) 导入项目
3. 自动检测 Next.js 框架
4. 点击部署

### 环境变量（可选）

创建 `.env.local` 文件配置环境变量：

```bash
# 如果需要从外部 API 获取数据
NEXT_PUBLIC_API_URL=https://your-api.com
```

## 📱 移动端优化

- 响应式布局，支持 375px - 1440px 屏幕
- 触摸友好的交互设计
- 优化的加载性能（首屏 < 2 秒）
- 适配 Telegram 内置浏览器

## 🎨 自定义配置

### 修改主题颜色

编辑 `tailwind.config.ts`:

```typescript
theme: {
  extend: {
    colors: {
      accent: {
        blue: '#3b82f6',
        green: '#10b981',
        // 添加更多颜色
      }
    }
  }
}
```

### 修改刷新间隔

编辑各页面组件中的 `refreshInterval`:

```typescript
const { data } = useSWR('/api/status', fetcher, {
  refreshInterval: 30000, // 30秒，可自定义
})
```

## 📊 数据源说明

当前版本使用硬编码的模拟数据。要连接真实数据源：

1. **Git 提交数据**: 修改 `/api/commits/route.ts`，使用 `child_process` 执行 `git log`
2. **测试结果**: 修改 `/api/tests/route.ts`，读取 `pytest` 输出或 JUnit XML
3. **对齐度数据**: 修改 `/api/parity/route.ts`，解析 `docs/openclaw-parity-matrix.md`
4. **Agent 状态**: 修改 `/api/agents/route.ts`，连接到真实的监控系统

## 🔧 开发建议

### 添加新页面

1. 在 `app/` 目录创建新文件夹
2. 添加 `page.tsx` 文件
3. 在 `components/Navigation.tsx` 添加导航链接

### 添加新 API

1. 在 `app/api/` 目录创建新文件夹
2. 添加 `route.ts` 文件
3. 导出 `GET` / `POST` 函数

### 添加新组件

1. 在 `components/` 目录创建新文件
2. 使用 `'use client'` 标记客户端组件
3. 在页面中导入使用

## 📝 待办事项

- [ ] 连接真实 Git 数据源
- [ ] 集成 CI/CD 测试结果
- [ ] 添加 WebSocket 实时推送
- [ ] 支持多语言（i18n）
- [ ] 添加暗色/亮色主题切换
- [ ] 集成错误追踪（Sentry）

## 🤝 贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解详情。

## 📄 许可证

MIT License - 详见 [LICENSE](../LICENSE)

---

**一起构建未来！** 🚀
