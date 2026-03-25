'use client'

import { ReactNode } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  color?: 'blue' | 'green' | 'purple' | 'red' | 'yellow' | 'cyan'
}

const colorClasses = {
  blue: 'from-accent-blue/20 to-accent-blue/5 border-accent-blue/30',
  green: 'from-accent-green/20 to-accent-green/5 border-accent-green/30',
  purple: 'from-accent-purple/20 to-accent-purple/5 border-accent-purple/30',
  red: 'from-accent-red/20 to-accent-red/5 border-accent-red/30',
  yellow: 'from-accent-yellow/20 to-accent-yellow/5 border-accent-yellow/30',
  cyan: 'from-accent-cyan/20 to-accent-cyan/5 border-accent-cyan/30',
}

export default function StatCard({ title, value, subtitle, icon, trend, color = 'blue' }: StatCardProps) {
  return (
    <div
      className={`
        bg-gradient-to-br ${colorClasses[color]}
        border rounded-xl p-6 card-hover
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-dark-400 mb-1">{title}</p>
          <p className="text-3xl font-bold text-white mb-1">{value}</p>
          {subtitle && <p className="text-xs text-dark-500">{subtitle}</p>}
        </div>
        {icon && (
          <div className="text-dark-400">
            {icon}
          </div>
        )}
      </div>

      {trend && (
        <div className="flex items-center mt-3 space-x-1">
          {trend.isPositive ? (
            <TrendingUp className="w-4 h-4 text-accent-green" />
          ) : (
            <TrendingDown className="w-4 h-4 text-accent-red" />
          )}
          <span className={`text-sm ${trend.isPositive ? 'text-accent-green' : 'text-accent-red'}`}>
            {trend.isPositive ? '+' : ''}{trend.value}%
          </span>
          <span className="text-xs text-dark-500">vs last week</span>
        </div>
      )}
    </div>
  )
}
