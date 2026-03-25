import { NextResponse } from 'next/server'

export async function GET() {
  const commits = [
    {
      hash: 'a3f8d2c',
      message: 'feat: implement P4 self-integration protocol (discover/prototype/promote)',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 3600000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'b7e4f1a',
      message: 'feat: add panel security with zero-trust architecture',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 7200000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'c9a2b5d',
      message: 'fix: resolve AppleDouble pollution in Docker containers',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 14400000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'd4c3e6f',
      message: 'feat: implement Telegram gateway with magic link authentication',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 21600000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'e5d7a8b',
      message: 'feat: add SQLite persistence for session management',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 28800000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'f6e9c2a',
      message: 'docs: update roadmap with milestone tracking',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 43200000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'a7f1b3c',
      message: 'test: add integration tests for Telegram webhook',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 57600000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'b8g2d4e',
      message: 'refactor: optimize context block for MCP tools',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 72000000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'c9h3e5f',
      message: 'feat: implement dynamic tool synthesis with Docker sandbox',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 86400000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
    {
      hash: 'd0i4f6g',
      message: 'docs: add critical design decisions document',
      author: 'srxly888-creator',
      date: new Date(Date.now() - 172800000).toISOString(),
      branch: 'codex/continue-autonomous-agent-stack',
    },
  ]

  return NextResponse.json({ commits, total: commits.length })
}
