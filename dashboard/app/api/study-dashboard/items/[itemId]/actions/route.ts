import { NextRequest, NextResponse } from 'next/server'

import { postControlPlaneJson } from '@/lib/controlPlane'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ itemId: string }> },
) {
  const body = await request.json().catch(() => ({}))
  const { itemId } = await params
  const result = await postControlPlaneJson(
    `/api/v1/study-dashboard/items/${itemId}/actions`,
    body,
  )
  return NextResponse.json(result)
}
