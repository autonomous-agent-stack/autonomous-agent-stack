import { NextRequest, NextResponse } from 'next/server'

import { postControlPlaneJson } from '@/lib/controlPlane'

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}))
  const result = await postControlPlaneJson('/api/v1/study-dashboard/briefs/daily', body)
  return NextResponse.json(result, { status: 201 })
}
