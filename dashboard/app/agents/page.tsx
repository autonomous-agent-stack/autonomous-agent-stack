'use client'

import useSWR from 'swr'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend } from 'recharts'
import { Users, Activity, TrendingUp } from 'lucide-react'
import Navigation from '@/components/Navigation'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

export default function AgentsPage() {
  const { data: agentsData, error } = useSWR('/api/agents', fetcher, {
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

  const agents = agentsData?.agents || []

  // 柱状图数据：运行时间对比
  const responseTimeData = agents.map((agent: any) => ({
    name: agent.name.replace(' Agent', ''),
    响应时间: parseFloat(agent.avgResponseTime),
  }))

  // 雷达图数据：协作矩阵
  const radarData = [
    { subject: '成功率', A: agents[0]?.successRate || 0, fullMark: 100 },
    { subject: '任务完成', A: (agents[0]?.tasksCompleted || 0) / 3, fullMark: 100 },
    { subject: '响应速度', A: 100 - parseFloat(agents[0]?.avgResponseTime || '0') * 30, fullMark: 100 },
    { subject: '稳定性', A: agents[0]?.successRate || 0, fullMark: 100 },
    { subject: '并发能力', A: 75, fullMark: 100 },
  ]

  // 协作矩阵
  const collaborationMatrix = [
    ['✓', '✓', '✓', '✓', '○', '✓', '○', '✓', '○', '○'],
    ['✓', '✓', '✓', '✓', '✓', '✓', '○', '✓', '✓', '○'],
    ['✓', '✓', '✓', '✓', '✓', '✓', '✓', '✓', '✓', '○'],
    ['✓', '✓', '✓', '✓', '✓', '✓', '○', '✓', '✓', '○'],
    ['○', '✓', '✓', '✓', '✓', '✓', '○', '✓', '○', '○'],
    ['✓', '✓', '✓', '✓', '✓', '✓', '○', '✓', '✓', '○'],
    ['○', '○', '✓', '○', '○', '○', '✓', '○', '○', '○'],
    ['✓', '✓', '✓', '✓', '✓', '✓', '○', '✓', '✓', '○'],
    ['○', '✓', '✓', '✓', '○', '✓', '○', '✓', '✓', '○'],
    ['○', '○', '○', '○', '○', '○', '○', '○', '○', '✓'],
  ]

  const agentNames = agents.map((a: any) => a.name.replace(' Agent', '').replace(' Gateway', '').substring(0, 6))

  return (
    <>
      <Navigation />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Agent 协作矩阵</h1>
          <p className="text-dark-400">10-Agent 协作关系与性能对比</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <div className="flex items-center space-x-3">
              <Users className="w-8 h-8 text-accent-blue" />
              <div>
                <p className="text-sm text-dark-400">总 Agent 数</p>
                <p className="text-2xl font-bold text-white">{agents.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <div className="flex items-center space-x-3">
              <Activity className="w-8 h-8 text-accent-green" />
              <div>
                <p className="text-sm text-dark-400">活跃 Agent</p>
                <p className="text-2xl font-bold text-white">{agents.filter((a: any) => a.status === 'running').length}</p>
              </div>
            </div>
          </div>

          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <div className="flex items-center space-x-3">
              <TrendingUp className="w-8 h-8 text-accent-purple" />
              <div>
                <p className="text-sm text-dark-400">平均成功率</p>
                <p className="text-2xl font-bold text-white">
                  {agents.length > 0
                    ? `${(agents.reduce((sum: number, a: any) => sum + a.successRate, 0) / agents.length).toFixed(1)}%`
                    : '...'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Bar Chart */}
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">响应时间对比</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={responseTimeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={10} angle={-45} textAnchor="end" height={80} />
                <YAxis stroke="#64748b" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="响应时间" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Radar Chart */}
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Planner Agent 能力雷达</h3>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" stroke="#64748b" fontSize={12} />
                <PolarRadiusAxis stroke="#64748b" />
                <Radar name="Planner" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.5} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Collaboration Matrix */}
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">10-Agent 协作矩阵</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="p-2"></th>
                  {agentNames.map((name: string, i: number) => (
                    <th key={i} className="p-2 text-dark-400 font-medium">
                      {name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {collaborationMatrix.map((row, i) => (
                  <tr key={i}>
                    <td className="p-2 text-dark-400 font-medium text-right">{agentNames[i]}</td>
                    {row.map((cell, j) => (
                      <td
                        key={j}
                        className={`
                          p-2 text-center border border-dark-700
                          ${i === j ? 'bg-accent-blue/10' : ''}
                        `}
                      >
                        <span
                          className={`
                            inline-block w-4 h-4 rounded-full
                            ${cell === '✓' ? 'bg-accent-green' : 'bg-dark-700'}
                          `}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center space-x-4 text-xs text-dark-400">
            <div className="flex items-center space-x-2">
              <span className="inline-block w-3 h-3 rounded-full bg-accent-green"></span>
              <span>可协作</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="inline-block w-3 h-3 rounded-full bg-dark-700"></span>
              <span>独立运行</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="inline-block w-3 h-3 rounded-full bg-accent-blue/30"></span>
              <span>自身</span>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}
