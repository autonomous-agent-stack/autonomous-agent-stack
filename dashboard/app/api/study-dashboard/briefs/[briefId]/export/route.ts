import { NextRequest, NextResponse } from 'next/server'

import { postControlPlaneJson } from '@/lib/controlPlane'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ briefId: string }> },
) {
  const body = await request.json().catch(() => ({}))
  const { briefId } = await params
  const result = await postControlPlaneJson(
    `/api/v1/study-dashboard/briefs/${briefId}/export`,
    body,
  )
  return NextResponse.json(result)
}
