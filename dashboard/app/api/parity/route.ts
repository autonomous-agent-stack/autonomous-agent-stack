import { NextResponse } from 'next/server'

import { fetchControlPlaneHealth } from '@/lib/controlPlane'

export async function GET() {
  await fetchControlPlaneHealth()

  return NextResponse.json({
    overall: 0,
    lastUpdated: new Date().toISOString(),
    categories: [],
    gaps: [],
    source: {
      mode: 'prototype-readonly',
      notes: ['parity page has no direct control-plane backing endpoint yet; empty state returned intentionally'],
    },
  })
}
