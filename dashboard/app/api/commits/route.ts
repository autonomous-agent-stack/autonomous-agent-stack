import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    commits: [],
    source: {
      mode: 'prototype-readonly',
      notes: ['commit feed is not wired to a read-only control-plane source yet; dashboard-local empty state returned intentionally'],
    },
  })
}
