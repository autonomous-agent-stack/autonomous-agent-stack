'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity, TestTube, GitBranch, Users } from 'lucide-react'

const navItems = [
  { href: '/', label: '首页', icon: Activity },
  { href: '/tests', label: '测试', icon: TestTube },
  { href: '/parity', label: '对齐', icon: GitBranch },
  { href: '/agents', label: 'Agents', icon: Users },
]

export default function Navigation() {
  const pathname = usePathname()

  return (
    <nav className="sticky top-0 z-50 bg-dark-900/80 backdrop-blur-lg border-b border-dark-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-accent-blue to-accent-purple rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white">Agent Stack</span>
          </div>

          <div className="flex space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                    flex items-center space-x-2 px-4 py-2 rounded-lg transition-all
                    ${
                      isActive
                        ? 'bg-accent-blue text-white shadow-lg shadow-accent-blue/25'
                        : 'text-dark-300 hover:text-white hover:bg-dark-800'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-sm font-medium hidden sm:inline">{item.label}</span>
                </Link>
              )
            })}
          </div>
        </div>
      </div>
    </nav>
  )
}
