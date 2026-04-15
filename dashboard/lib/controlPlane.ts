const DEFAULT_CONTROL_PLANE_BASE_URL = 'http://127.0.0.1:8001'

type ControlPlaneHealth = {
  status?: string
}

type ControlPlaneAgentRun = {
  agent_run_id: string
  task_name: string
  status: string
  agent_name?: string | null
  session_id?: string | null
  generation_depth?: number
  duration_seconds?: number | null
  created_at: string
  updated_at: string
  error?: string | null
}

export type DashboardAgent = {
  id: string
  name: string
  status: 'running' | 'idle' | 'error'
  successRate: number
  tasksCompleted: number
  avgResponseTime: string
  lastActivity: string
  role: string
}

export function getControlPlaneBaseUrl(): string {
  const configured =
    process.env.DASHBOARD_CONTROL_PLANE_BASE_URL ||
    process.env.NEXT_PUBLIC_CONTROL_PLANE_BASE_URL ||
    DEFAULT_CONTROL_PLANE_BASE_URL
  return configured.replace(/\/+$/, '')
}

async function fetchControlPlaneJson<T>(path: string): Promise<T> {
  const response = await fetch(`${getControlPlaneBaseUrl()}${path}`, {
    headers: {
      Accept: 'application/json',
    },
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error(`control-plane request failed: ${path} -> ${response.status}`)
  }

  return (await response.json()) as T
}

export async function fetchControlPlaneHealth(): Promise<ControlPlaneHealth> {
  return fetchControlPlaneJson<ControlPlaneHealth>('/health')
}

export async function fetchControlPlaneAgents(): Promise<ControlPlaneAgentRun[]> {
  return fetchControlPlaneJson<ControlPlaneAgentRun[]>('/api/v1/openclaw/agents')
}

function mapAgentStatus(status: string): DashboardAgent['status'] {
  switch (status) {
    case 'running':
      return 'running'
    case 'failed':
      return 'error'
    default:
      return 'idle'
  }
}

function formatDuration(durationSeconds?: number | null): string {
  if (!durationSeconds || durationSeconds <= 0) {
    return 'n/a'
  }
  if (durationSeconds < 1) {
    return `${Math.round(durationSeconds * 1000)}ms`
  }
  if (durationSeconds < 60) {
    return `${durationSeconds.toFixed(1)}s`
  }
  const minutes = Math.floor(durationSeconds / 60)
  const seconds = Math.round(durationSeconds % 60)
  return `${minutes}m ${seconds}s`
}

function buildRole(run: ControlPlaneAgentRun): string {
  if (run.agent_name && run.agent_name.trim()) {
    return run.agent_name
  }
  if (run.session_id) {
    return `session ${run.session_id}`
  }
  return 'openclaw agent'
}

function buildSuccessRate(run: ControlPlaneAgentRun): number {
  if (run.status === 'failed') {
    return 0
  }
  if (run.status === 'completed') {
    return 100
  }
  return 50
}

function buildTasksCompleted(run: ControlPlaneAgentRun): number {
  return run.status === 'completed' ? 1 : 0
}

export function mapAgentRunToDashboardAgent(run: ControlPlaneAgentRun): DashboardAgent {
  return {
    id: run.agent_run_id,
    name: run.task_name,
    status: mapAgentStatus(run.status),
    successRate: buildSuccessRate(run),
    tasksCompleted: buildTasksCompleted(run),
    avgResponseTime: formatDuration(run.duration_seconds),
    lastActivity: run.updated_at,
    role: buildRole(run),
  }
}

export function summarizeDashboardAgents(agents: DashboardAgent[]) {
  const totalAgents = agents.length
  const activeAgents = agents.filter((agent) => agent.status === 'running').length
  const completedAgents = agents.filter((agent) => agent.status === 'idle' && agent.tasksCompleted > 0).length
  const failedAgents = agents.filter((agent) => agent.status === 'error').length
  const successRate = totalAgents > 0
    ? Number((agents.reduce((sum, agent) => sum + agent.successRate, 0) / totalAgents).toFixed(1))
    : 0

  return {
    totalAgents,
    activeAgents,
    completedAgents,
    failedAgents,
    successRate,
  }
}
