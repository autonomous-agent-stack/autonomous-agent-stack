'use client'

import { GitCommit, GitBranch } from 'lucide-react'

interface Commit {
  hash: string
  message: string
  author: string
  date: string
  branch: string
}

interface CommitListProps {
  commits: Commit[]
}

export default function CommitList({ commits }: CommitListProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}天前`
    if (hours > 0) return `${hours}小时前`
    return '刚刚'
  }

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
        <GitCommit className="w-5 h-5 text-accent-purple" />
        <span>最近提交</span>
      </h3>

      <div className="space-y-4">
        {commits.slice(0, 5).map((commit) => (
          <div
            key={commit.hash}
            className="border-l-2 border-dark-600 pl-4 py-2 hover:border-accent-blue transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white font-medium truncate">{commit.message}</p>
                <div className="flex items-center space-x-3 mt-1">
                  <span className="text-xs text-dark-400 font-mono">{commit.hash}</span>
                  <span className="text-xs text-dark-500">by {commit.author}</span>
                </div>
              </div>
              <div className="flex items-center space-x-2 text-xs text-dark-500">
                <GitBranch className="w-3 h-3" />
                <span>{commit.branch.replace('codex/', '')}</span>
              </div>
            </div>
            <p className="text-xs text-dark-500 mt-1">{formatDate(commit.date)}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
