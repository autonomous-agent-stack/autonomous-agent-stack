'use client'

import useSWR from 'swr'
import { GitBranch, CheckCircle, Clock, AlertTriangle } from 'lucide-react'
import Navigation from '@/components/Navigation'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

export default function ParityPage() {
  const { data: parity, error } = useSWR('/api/parity', fetcher, {
    refreshInterval: 30000,
  })

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 text-lg">加载失败</p>
          <p className="text-dark-400 text-sm mt-2">请检查网络连接或刷新页面</p>
        </div>
      </div>
    )
  }

  const priorityColors = {
    P0: 'bg-accent-red',
    P1: 'bg-accent-yellow',
    P2: 'bg-accent-blue',
  }

  return (
    <>
      <Navigation />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">OpenClaw 对齐度</h1>
          <p className="text-dark-400">查看功能完成度和缺口分析</p>
        </div>

        {/* Overall Progress */}
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <GitBranch className="w-8 h-8 text-accent-purple" />
              <div>
                <p className="text-sm text-dark-400">整体对齐度</p>
                <p className="text-4xl font-bold text-white">{parity?.overall ? `${parity.overall}%` : '...'}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-dark-400">最后更新</p>
              <p className="text-sm text-white">
                {parity?.lastUpdated ? new Date(parity.lastUpdated).toLocaleString('zh-CN') : '...'}
              </p>
            </div>
          </div>

          <div className="w-full h-4 bg-dark-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent-blue to-accent-purple transition-all duration-1000"
              style={{ width: `${parity?.overall || 0}%` }}
            />
          </div>
        </div>

        {/* Categories */}
        <div className="space-y-4 mb-8">
          {parity?.categories.map((category: any, index: number) => (
            <div key={index} className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${priorityColors[category.priority as keyof typeof priorityColors]}`}>
                    {category.priority}
                  </span>
                  <h3 className="text-lg font-semibold text-white">{category.name}</h3>
                </div>
                <span className="text-2xl font-bold text-white">{category.progress}%</span>
              </div>

              <div className="w-full h-2 bg-dark-700 rounded-full overflow-hidden mb-4">
                <div
                  className={`h-full ${
                    category.progress === 100
                      ? 'bg-accent-green'
                      : category.progress >= 75
                      ? 'bg-accent-blue'
                      : category.progress >= 50
                      ? 'bg-accent-yellow'
                      : 'bg-accent-red'
                  }`}
                  style={{ width: `${category.progress}%` }}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {category.features.map((feature: any, fIndex: number) => (
                  <div key={fIndex} className="flex items-center justify-between bg-dark-900/50 rounded-lg p-3">
                    <div className="flex items-center space-x-2">
                      {feature.status === 'completed' ? (
                        <CheckCircle className="w-4 h-4 text-accent-green" />
                      ) : feature.status === 'in_progress' ? (
                        <Clock className="w-4 h-4 text-accent-yellow" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-dark-500" />
                      )}
                      <span className="text-sm text-white">{feature.name}</span>
                    </div>
                    <span className="text-xs text-dark-400">{feature.completion}%</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Gaps */}
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">缺口功能清单</h3>
          <div className="space-y-3">
            {parity?.gaps.map((gap: any, index: number) => (
              <div key={index} className="border-l-4 border-accent-yellow pl-4 py-3 bg-dark-900/50 rounded-r">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold ${priorityColors[gap.priority as keyof typeof priorityColors]} text-white`}>
                        {gap.priority}
                      </span>
                      <h4 className="text-sm font-medium text-white">{gap.feature}</h4>
                    </div>
                    <p className="text-xs text-dark-400">{gap.description}</p>
                  </div>
                  <span className="text-xs text-dark-500 ml-4">{gap.estimatedEffort}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  )
}
