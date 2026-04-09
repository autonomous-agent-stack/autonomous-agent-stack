import { NextResponse } from 'next/server'

import { fetchControlPlaneHealth } from '@/lib/controlPlane'

export async function GET() {
  await fetchControlPlaneHealth()

  return NextResponse.json({
    summary: {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      passRate: 0,
    },
    categories: [],
    failedTests: [],
    lastRun: new Date().toISOString(),
    source: {
      mode: 'prototype-readonly',
      notes: ['tests page has no direct control-plane backing endpoint yet; empty state returned intentionally'],
    },
  })
}
