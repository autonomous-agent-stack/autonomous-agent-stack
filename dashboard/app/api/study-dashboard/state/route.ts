import { NextResponse } from 'next/server'

import { fetchControlPlaneJson } from '@/lib/controlPlane'

export const dynamic = 'force-dynamic'

export async function GET() {
  const state = await fetchControlPlaneJson('/api/v1/study-dashboard/state')
  return NextResponse.json(state)
}
