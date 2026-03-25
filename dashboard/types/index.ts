// Type definitions for the dashboard

export interface Agent {
  id: string
  name: string
  status: 'running' | 'idle' | 'error'
  successRate: number
  tasksCompleted: number
  avgResponseTime: string
  lastActivity: string
  role: string
}

export interface Commit {
  hash: string
  message: string
  author: string
  date: string
  branch: string
}

export interface TestResult {
  name: string
  status: 'passed' | 'failed' | 'skipped'
  duration: string
  error?: string
}

export interface TestCategory {
  name: string
  total: number
  passed: number
  failed: number
  tests: TestResult[]
}

export interface TestsData {
  summary: {
    total: number
    passed: number
    failed: number
    skipped: number
    passRate: number
  }
  categories: TestCategory[]
  failedTests: Array<{
    name: string
    error: string
    duration: string
    category: string
  }>
  lastRun: string
}

export interface Feature {
  name: string
  status: 'completed' | 'in_progress' | 'pending'
  completion: number
}

export interface Category {
  name: string
  priority: 'P0' | 'P1' | 'P2'
  progress: number
  features: Feature[]
}

export interface Gap {
  priority: 'P0' | 'P1' | 'P2'
  feature: string
  description: string
  estimatedEffort: string
}

export interface ParityData {
  overall: number
  lastUpdated: string
  categories: Category[]
  gaps: Gap[]
}

export interface StatusData {
  projectName: string
  version: string
  overallProgress: number
  successRate: number
  uptime: string
  lastUpdated: string
  health: 'healthy' | 'degraded' | 'down'
  metrics: {
    totalAgents: number
    activeAgents: number
    totalTests: number
    passedTests: number
    failedTests: number
    pendingTasks: number
  }
  features: {
    p0: { total: number; completed: number }
    p1: { total: number; completed: number }
    p2: { total: number; completed: number }
  }
}
