import { NextResponse } from 'next/server'

import { fetchControlPlaneHealth } from '@/lib/controlPlane'

export async function GET() {
  await fetchControlPlaneHealth()

  return NextResponse.json({
    commits: [],
    source: {
      mode: 'prototype-readonly',
      notes: ['commit feed is not wired to a read-only control-plane source yet'],
    },
  })
}
