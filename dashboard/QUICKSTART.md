# 🚀 Quick Start Guide

快速启动 Autonomous Agent Stack Dashboard。

## 前置要求

- Node.js 18+ 
- npm 或 yarn

## 3 步启动

### 1. 安装依赖

```bash
cd dashboard
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

或者使用脚本：

```bash
./scripts/dev.sh
```

### 3. 打开浏览器

访问 http://localhost:3000

## 📱 移动端测试

### 在 Telegram 中打开

1. 启动开发服务器
2. 获取本地 IP 地址：
   ```bash
   # macOS
   ipconfig getifaddr en0
   
   # Linux
   hostname -I
   ```
3. 在手机浏览器中打开：`http://<你的IP>:3000`
4. 或者通过 Telegram 机器人分享链接

## 🎨 页面导航

- **首页** (`/`) - 项目概览和 Agent 状态
- **测试** (`/tests`) - 测试结果和失败详情
- **对齐** (`/parity`) - OpenClaw 功能对齐度
- **Agents** (`/agents`) - 10-Agent 协作矩阵

## 🔧 常见问题

### 端口被占用

修改 `package.json` 中的端口：

```json
"dev": "next dev -p 3001"
```

### 样式不生效

清除缓存并重启：

```bash
rm -rf .next node_modules
npm install
npm run dev
```

### API 数据不更新

检查 API 端点是否返回正确的数据格式，或修改刷新间隔（默认 30 秒）。

## 🚀 部署到 Vercel

```bash
# 安装 Vercel CLI
npm i -g vercel

# 部署
vercel
```

## 📊 自定义数据

修改以下文件以连接真实数据源：

- `/api/status/route.ts` - 项目状态
- `/api/agents/route.ts` - Agent 数据
- `/api/tests/route.ts` - 测试结果
- `/api/parity/route.ts` - 对齐度数据
- `/api/commits/route.ts` - Git 提交记录

## 🎯 下一步

1. [ ] 截图保存到 `public/screenshots/`
2. [ ] 修改 API 端点连接真实数据
3. [ ] 部署到 Vercel 或本地服务器
4. [ ] 在 Telegram 群组中分享链接

---

需要帮助？查看 [README.md](./README.md)
