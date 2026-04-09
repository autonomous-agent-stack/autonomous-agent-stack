import { NextResponse } from 'next/server'

import { fetchControlPlaneAgents, mapAgentRunToDashboardAgent } from '@/lib/controlPlane'

export async function GET() {
  const agentRuns = await fetchControlPlaneAgents()

  return NextResponse.json({
    agents: agentRuns.map(mapAgentRunToDashboardAgent),
    source: {
      mode: 'prototype-readonly',
      notes: ['mapped from /api/v1/openclaw/agents'],
    },
  })
}
