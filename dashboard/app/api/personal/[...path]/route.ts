import { NextRequest, NextResponse } from 'next/server'

import { fetchControlPlaneJson, postControlPlaneJson } from '@/lib/controlPlane'

type RouteParams = {
  params: Promise<{
    path?: string[]
  }>
}

function personalPath(params: Awaited<RouteParams['params']>, request?: NextRequest) {
  const suffix = (params.path || []).join('/')
  const query = request?.nextUrl.search || ''
  return `/api/v1/personal/${suffix}${query}`
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const result = await fetchControlPlaneJson(personalPath(await params, request))
  return NextResponse.json(result)
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const body = await request.json().catch(() => ({}))
  const result = await postControlPlaneJson(personalPath(await params), body)
  return NextResponse.json(result)
}
