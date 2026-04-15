import { NextResponse } from 'next/server'

import {
  fetchControlPlaneAgents,
  fetchControlPlaneHealth,
  mapAgentRunToDashboardAgent,
  summarizeDashboardAgents,
} from '@/lib/controlPlane'

export async function GET() {
  const [health, agentRuns] = await Promise.all([
    fetchControlPlaneHealth(),
    fetchControlPlaneAgents(),
  ])

  const agents = agentRuns.map(mapAgentRunToDashboardAgent)
  const summary = summarizeDashboardAgents(agents)
  const now = new Date().toISOString()

  return NextResponse.json({
    projectName: 'Autonomous Agent Stack Dashboard',
    version: 'prototype-readonly',
    overallProgress: 0,
    successRate: summary.successRate,
    uptime: 'n/a',
    lastUpdated: now,
    health: health.status === 'ok' ? 'healthy' : 'degraded',
    metrics: {
      totalAgents: summary.totalAgents,
      activeAgents: summary.activeAgents,
      totalTests: 0,
      passedTests: 0,
      failedTests: 0,
      pendingTasks: summary.totalAgents - summary.completedAgents - summary.failedAgents,
    },
    features: {
      p0: { total: 0, completed: 0 },
      p1: { total: 0, completed: 0 },
      p2: { total: 0, completed: 0 },
    },
    source: {
      mode: 'prototype-readonly',
      controlPlaneBaseUrl: 'http://127.0.0.1:8001',
      notes: ['status and agents come from existing control-plane read-only endpoints'],
    },
  })
}
