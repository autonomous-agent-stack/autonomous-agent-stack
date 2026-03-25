'use client'

import useSWR from 'swr'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import { TestTube, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import Navigation from '@/components/Navigation'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

const COLORS = {
  passed: '#10b981',
  failed: '#ef4444',
  skipped: '#64748b',
}

export default function TestsPage() {
  const { data: tests, error } = useSWR('/api/tests', fetcher, {
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

  const pieData = tests
    ? [
        { name: '通过', value: tests.summary.passed, color: COLORS.passed },
        { name: '失败', value: tests.summary.failed, color: COLORS.failed },
        { name: '跳过', value: tests.summary.skipped, color: COLORS.skipped },
      ]
    : []

  return (
    <>
      <Navigation />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">测试结果</h1>
          <p className="text-dark-400">查看测试用例执行情况和失败详情</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <div className="flex items-center space-x-3">
              <TestTube className="w-8 h-8 text-accent-blue" />
              <div>
                <p className="text-sm text-dark-400">总测试数</p>
                <p className="text-2xl font-bold text-white">{tests?.summary.total || '...'}</p>
              </div>
            </div>
          </div>

          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-8 h-8 text-accent-green" />
              <div>
                <p className="text-sm text-dark-400">通过</p>
                <p className="text-2xl font-bold text-white">{tests?.summary.passed || '...'}</p>
              </div>
            </div>
          </div>

          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <div className="flex items-center space-x-3">
              <XCircle className="w-8 h-8 text-accent-red" />
              <div>
                <p className="text-sm text-dark-400">失败</p>
                <p className="text-2xl font-bold text-white">{tests?.summary.failed || '...'}</p>
              </div>
            </div>
          </div>

          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-8 h-8 text-accent-yellow" />
              <div>
                <p className="text-sm text-dark-400">通过率</p>
                <p className="text-2xl font-bold text-white">{tests?.summary.passRate ? `${tests.summary.passRate}%` : '...'}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pie Chart */}
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">测试通过率</h3>
            {tests && (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Failed Tests */}
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">失败测试详情</h3>
            <div className="space-y-3">
              {tests?.failedTests.map((test: any, index: number) => (
                <div
                  key={index}
                  className="border-l-4 border-accent-red pl-4 py-2 bg-dark-900/50 rounded-r"
                >
                  <p className="text-sm font-medium text-white font-mono">{test.name}</p>
                  <p className="text-xs text-dark-400 mt-1">{test.error}</p>
                  <div className="flex items-center space-x-2 mt-2">
                    <span className="text-xs text-dark-500">{test.duration}</span>
                    <span className="text-xs text-dark-600">•</span>
                    <span className="text-xs text-dark-500">{test.category}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Test Categories */}
        <div className="mt-6 bg-dark-800/50 border border-dark-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">测试分类</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tests?.categories.map((category: any, index: number) => (
              <div key={index} className="bg-dark-900/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-white">{category.name}</h4>
                  <span className="text-xs text-dark-400">
                    {category.passed}/{category.total}
                  </span>
                </div>
                <div className="w-full h-2 bg-dark-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent-green"
                    style={{ width: `${(category.passed / category.total) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 text-center text-dark-500 text-sm">
          <p>最后运行: {tests?.lastRun ? new Date(tests.lastRun).toLocaleString('zh-CN') : '...'}</p>
        </div>
      </main>
    </>
  )
}
