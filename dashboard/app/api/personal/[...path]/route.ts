import { NextRequest, NextResponse } from 'next/server'

import { getControlPlaneBaseUrl } from '@/lib/controlPlane'

type RouteParams = {
  params: Promise<{
    path?: string[]
  }>
}

function isRemoteModeEnabled() {
  const raw =
    process.env.AUTORESEARCH_PERSONAL_REMOTE_ENABLED ||
    process.env.NEXT_PUBLIC_PERSONAL_REMOTE_ENABLED ||
    ''
  return ['1', 'true', 'yes', 'on'].includes(raw.trim().toLowerCase())
}

function personalPath(params: Awaited<RouteParams['params']>, request: NextRequest) {
  const suffix = (params.path || []).join('/')
  const query = request.nextUrl.search || ''
  return `/api/v1/personal/${suffix}${query}`
}

function tokenFrom(request: NextRequest) {
  const authorization = request.headers.get('authorization') || ''
  const token = request.nextUrl.searchParams.get('token') || ''
  return authorization.trim() || token.trim()
}

async function proxyPersonal(request: NextRequest, params: Awaited<RouteParams['params']>, method: 'GET' | 'POST') {
  if (isRemoteModeEnabled() && !tokenFrom(request)) {
    return NextResponse.json(
      { status: 'failed', reason: 'personal remote token required' },
      { status: 401 },
    )
  }

  const headers: Record<string, string> = {
    Accept: 'application/json',
  }
  const authorization = request.headers.get('authorization')
  const token = request.nextUrl.searchParams.get('token')
  if (authorization) {
    headers.Authorization = authorization
  } else if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  let body: string | undefined
  if (method === 'POST') {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(await request.json().catch(() => ({})))
  }

  const response = await fetch(`${getControlPlaneBaseUrl()}${personalPath(params, request)}`, {
    method,
    headers,
    body,
    cache: 'no-store',
  })
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return NextResponse.json(await response.json(), { status: response.status })
  }
  return new NextResponse(await response.text(), { status: response.status })
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  return proxyPersonal(request, await params, 'GET')
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  return proxyPersonal(request, await params, 'POST')
}
