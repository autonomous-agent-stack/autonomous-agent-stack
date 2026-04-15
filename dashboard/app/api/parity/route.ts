import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    overall: 0,
    lastUpdated: new Date().toISOString(),
    categories: [],
    gaps: [],
    source: {
      mode: 'prototype-readonly',
      notes: ['parity page has no direct control-plane backing endpoint yet; dashboard-local empty state returned intentionally'],
    },
  })
}
