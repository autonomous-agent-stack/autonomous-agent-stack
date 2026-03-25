'use client'

import { Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

interface Agent {
  id: string
  name: string
  status: 'running' | 'idle' | 'error'
  successRate: number
  tasksCompleted: number
  avgResponseTime: string
  lastActivity: string
  role: string
}

interface AgentTableProps {
  agents: Agent[]
}

const statusConfig = {
  running: { icon: CheckCircle, color: 'text-accent-green', label: '运行中' },
  idle: { icon: Clock, color: 'text-accent-yellow', label: '空闲' },
  error: { icon: XCircle, color: 'text-accent-red', label: '错误' },
}

export default function AgentTable({ agents }: AgentTableProps) {
  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-dark-800 border-b border-dark-700">
              <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                Agent
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                状态
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                成功率
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                完成任务
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                响应时间
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700">
            {agents.map((agent) => {
              const status = statusConfig[agent.status]
              const Icon = status.icon

              return (
                <tr key={agent.id} className="hover:bg-dark-800/50 transition-colors">
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-white">{agent.name}</p>
                      <p className="text-xs text-dark-500">{agent.role}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className={`flex items-center space-x-2 ${status.color}`}>
                      <Icon className="w-4 h-4" />
                      <span className="text-sm">{status.label}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 h-2 bg-dark-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            agent.successRate >= 90
                              ? 'bg-accent-green'
                              : agent.successRate >= 80
                              ? 'bg-accent-yellow'
                              : 'bg-accent-red'
                          }`}
                          style={{ width: `${agent.successRate}%` }}
                        />
                      </div>
                      <span className="text-sm text-white font-mono">{agent.successRate}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-white font-mono">{agent.tasksCompleted}</td>
                  <td className="px-4 py-3 text-sm text-dark-300 font-mono">{agent.avgResponseTime}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
