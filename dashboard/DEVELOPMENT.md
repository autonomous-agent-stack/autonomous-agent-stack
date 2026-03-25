# 🛠️ Development Guide

Dashboard 开发指南。

## 项目结构

```
dashboard/
├── app/                    # Next.js App Router
│   ├── api/               # API 端点
│   │   ├── status/        # 项目状态
│   │   ├── agents/        # Agent 列表
│   │   ├── tests/         # 测试结果
│   │   ├── parity/        # 对齐度数据
│   │   └── commits/       # Git 提交
│   ├── agents/            # Agent 页面
│   ├── tests/             # 测试页面
│   ├── parity/            # 对齐页面
│   ├── layout.tsx         # 根布局
│   ├── page.tsx           # 首页
│   └── globals.css        # 全局样式
├── components/            # React 组件
│   ├── Navigation.tsx     # 导航栏
│   ├── StatCard.tsx       # 统计卡片
│   ├── AgentTable.tsx     # Agent 表格
│   └── CommitList.tsx     # 提交列表
├── lib/                   # 工具函数
│   └── utils.ts
├── types/                 # TypeScript 类型
│   └── index.ts
├── public/                # 静态资源
│   └── screenshots/       # 截图
└── scripts/               # 脚本
    ├── dev.sh            # 开发脚本
    └── deploy.sh         # 部署脚本
```

## 添加新页面

1. 创建页面文件：

```bash
# 创建新页面目录
mkdir -p app/new-page

# 创建页面组件
touch app/new-page/page.tsx
```

2. 实现页面组件：

```tsx
// app/new-page/page.tsx
'use client'

import Navigation from '@/components/Navigation'

export default function NewPage() {
  return (
    <>
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-white">新页面</h1>
      </main>
    </>
  )
}
```

3. 在导航栏添加链接：

```tsx
// components/Navigation.tsx
const navItems = [
  // ...
  { href: '/new-page', label: '新页面', icon: Icon },
]
```

## 添加新 API 端点

1. 创建 API 目录：

```bash
mkdir -p app/api/new-endpoint
touch app/api/new-endpoint/route.ts
```

2. 实现 API 处理器：

```ts
// app/api/new-endpoint/route.ts
import { NextResponse } from 'next/server'

export async function GET() {
  const data = {
    message: 'Hello World',
  }

  return NextResponse.json(data)
}
```

3. 在组件中使用：

```tsx
import useSWR from 'swr'

const { data } = useSWR('/api/new-endpoint', fetcher)
```

## 添加新组件

1. 创建组件文件：

```bash
touch components/NewComponent.tsx
```

2. 实现组件：

```tsx
// components/NewComponent.tsx
'use client'

interface NewComponentProps {
  title: string
  data: any[]
}

export default function NewComponent({ title, data }: NewComponentProps) {
  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      {/* 组件内容 */}
    </div>
  )
}
```

3. 在页面中使用：

```tsx
import NewComponent from '@/components/NewComponent'

<NewComponent title="标题" data={data} />
```

## 样式指南

### 颜色

- 背景：`bg-dark-900` / `bg-dark-800` / `bg-dark-700`
- 文字：`text-white` / `text-dark-400` / `text-dark-500`
- 强调：`text-accent-blue` / `text-accent-green` / `text-accent-purple`

### 间距

- 卡片内边距：`p-6`
- 网格间距：`gap-4` 或 `gap-6`
- 页面边距：`px-4 sm:px-6 lg:px-8 py-8`

### 响应式

```tsx
// 移动优先
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* 内容 */}
</div>
```

## 状态管理

使用 SWR 进行数据获取和缓存：

```tsx
import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

// 自动刷新（30秒）
const { data, error } = useSWR('/api/endpoint', fetcher, {
  refreshInterval: 30000,
})

// 手动重新验证
const { mutate } = useSWR('/api/endpoint', fetcher)
mutate()
```

## 图表使用

使用 Recharts 创建图表：

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

<ResponsiveContainer width="100%" height={300}>
  <BarChart data={data}>
    <XAxis dataKey="name" stroke="#64748b" />
    <YAxis stroke="#64748b" />
    <Tooltip
      contentStyle={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '8px',
      }}
    />
    <Bar dataKey="value" fill="#3b82f6" />
  </BarChart>
</ResponsiveContainer>
```

## 性能优化

### 1. 图片优化

```tsx
import Image from 'next/image'

<Image
  src="/path/to/image.png"
  alt="描述"
  width={800}
  height={600}
  loading="lazy"
/>
```

### 2. 代码分割

```tsx
import dynamic from 'next/dynamic'

const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <p>Loading...</p>,
})
```

### 3. 缓存策略

```tsx
// SWR 缓存配置
const { data } = useSWR('/api/data', fetcher, {
  refreshInterval: 30000,
  revalidateOnFocus: false,
  dedupingInterval: 60000,
})
```

## 调试

### 查看网络请求

1. 打开浏览器开发者工具
2. 切换到 Network 标签
3. 查看所有 API 请求

### 查看 SWR 状态

安装 SWR DevTools：

```bash
npm install swr-devtools
```

在 `_app.tsx` 中添加：

```tsx
import { SWRDevTools } from 'swr-devtools'

export default function App({ Component, pageProps }) {
  return (
    <SWRDevTools>
      <Component {...pageProps} />
    </SWRDevTools>
  )
}
```

## 测试

### 单元测试

```bash
npm test
```

### E2E 测试

使用 Playwright：

```bash
npm install -D @playwright/test
npx playwright test
```

## 部署

### Vercel

```bash
vercel --prod
```

### 自托管

```bash
npm run build
npm start
```

服务器将在 http://localhost:3000 运行。

## 常见问题

### 端口冲突

修改启动端口：

```json
{
  "scripts": {
    "dev": "next dev -p 3001"
  }
}
```

### 构建失败

清除缓存：

```bash
rm -rf .next
npm run build
```

### 类型错误

更新 TypeScript：

```bash
npm install -D typescript@latest @types/react@latest @types/node@latest
```

---

**Happy coding!** 🚀
