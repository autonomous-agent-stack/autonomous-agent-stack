import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Autonomous Agent Stack Dashboard',
  description: '实时监控 autonomous-agent-stack 项目状态、Agent 运行情况和测试结果',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
  themeColor: '#0f172a',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className={inter.className}>
        <div className="min-h-screen bg-gradient-to-b from-dark-900 to-dark-950">
          {children}
        </div>
      </body>
    </html>
  )
}
