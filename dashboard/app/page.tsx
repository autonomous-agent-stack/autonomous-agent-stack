'use client'

import useSWR from 'swr'
import { Activity, CheckCircle, Clock, TrendingUp } from 'lucide-react'
import Navigation from '@/components/Navigation'
import StatCard from '@/components/StatCard'
import AgentTable from '@/components/AgentTable'
import CommitList from '@/components/CommitList'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

export default function HomePage() {
  const { data: status, error: statusError } = useSWR('/api/status', fetcher, {
    refreshInterval: 30000,
  })
  const { data: agents, error: agentsError } = useSWR('/api/agents', fetcher, {
    refreshInterval: 30000,
  })
  const { data: commits, error: commitsError } = useSWR('/api/commits', fetcher, {
    refreshInterval: 30000,
  })

  if (statusError || agentsError || commitsError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 text-lg">加载失败</p>
          <p className="text-dark-400 text-sm mt-2">请检查网络连接或刷新页面</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <Navigation />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">项目概览</h1>
          <p className="text-dark-400">实时监控 Autonomous Agent Stack 项目状态</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="整体完成度"
            value={status?.overallProgress ? `${status.overallProgress}%` : '...'}
            subtitle="P0/P1/P2 功能"
            icon={<TrendingUp className="w-6 h-6" />}
            trend={{ value: 8, isPositive: true }}
            color="blue"
          />
          <StatCard
            title="成功率"
            value={status?.successRate ? `${status.successRate}%` : '...'}
            subtitle="Agent 执行成功率"
            icon={<CheckCircle className="w-6 h-6" />}
            trend={{ value: 3.2, isPositive: true }}
            color="green"
          />
          <StatCard
            title="运行时间"
            value={status?.uptime || '...'}
            subtitle="系统持续运行"
            icon={<Clock className="w-6 h-6" />}
            color="purple"
          />
          <StatCard
            title="活跃 Agents"
            value={status?.metrics ? `${status.metrics.activeAgents}/${status.metrics.totalAgents}` : '...'}
            subtitle="当前运行中"
            icon={<Activity className="w-6 h-6" />}
            color="cyan"
          />
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Agents Table */}
          <div className="lg:col-span-2">
            <h2 className="text-xl font-semibold text-white mb-4">Agent 状态</h2>
            {agents?.agents ? <AgentTable agents={agents.agents} /> : (
              <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8 text-center">
                <div className="animate-pulse text-dark-400">加载中...</div>
              </div>
            )}
          </div>

          {/* Commits */}
          <div className="lg:col-span-1">
            {commits?.commits ? <CommitList commits={commits.commits} /> : (
              <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8 text-center">
                <div className="animate-pulse text-dark-400">加载中...</div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-dark-500 text-sm">
          <p>最后更新: {status?.lastUpdated ? new Date(status.lastUpdated).toLocaleString('zh-CN') : '...'}</p>
        </div>
      </main>
    </>
  )
}
