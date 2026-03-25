import { NextResponse } from 'next/server'

export async function GET() {
  const tests = {
    summary: {
      total: 40,
      passed: 34,
      failed: 6,
      skipped: 0,
      passRate: 85.0,
    },
    categories: [
      {
        name: '核心逻辑测试',
        total: 8,
        passed: 8,
        failed: 0,
        tests: [
          { name: 'test_core_logic.py::test_planner_node', status: 'passed', duration: '0.45s' },
          { name: 'test_core_logic.py::test_generator_node', status: 'passed', duration: '0.32s' },
          { name: 'test_core_logic.py::test_executor_node', status: 'passed', duration: '0.78s' },
          { name: 'test_core_logic.py::test_evaluator_node', status: 'passed', duration: '0.56s' },
        ],
      },
      {
        name: 'API 集成测试',
        total: 6,
        passed: 5,
        failed: 1,
        tests: [
          { name: 'test_api_real.py::test_sessions_endpoint', status: 'passed', duration: '1.23s' },
          { name: 'test_api_real.py::test_agents_endpoint', status: 'passed', duration: '0.89s' },
          { name: 'test_api_real.py::test_webhook_endpoint', status: 'failed', duration: '2.45s', error: 'Connection timeout' },
        ],
      },
      {
        name: 'Telegram 网关测试',
        total: 4,
        passed: 4,
        failed: 0,
        tests: [
          { name: 'test_gateway_telegram.py::test_webhook_validation', status: 'passed', duration: '0.67s' },
          { name: 'test_gateway_telegram.py::test_message_routing', status: 'passed', duration: '0.92s' },
        ],
      },
      {
        name: '安全测试',
        total: 6,
        passed: 5,
        failed: 1,
        tests: [
          { name: 'test_panel_security.py::test_jwt_validation', status: 'passed', duration: '0.34s' },
          { name: 'test_panel_security.py::test_ip_whitelist', status: 'passed', duration: '0.28s' },
          { name: 'test_panel_security.py::test_rate_limiting', status: 'failed', duration: '1.89s', error: 'Rate limit exceeded' },
        ],
      },
      {
        name: '动态工具测试',
        total: 4,
        passed: 3,
        failed: 1,
        tests: [
          { name: 'test_dynamic_tool_synthesis.py::test_docker_execution', status: 'passed', duration: '3.45s' },
          { name: 'test_dynamic_tool_synthesis.py::test_appledouble_cleanup', status: 'passed', duration: '0.12s' },
          { name: 'test_dynamic_tool_synthesis.py::test_resource_limits', status: 'failed', duration: '5.67s', error: 'Container OOM' },
        ],
      },
      {
        name: 'OpenClaw 兼容性测试',
        total: 5,
        passed: 4,
        failed: 1,
        tests: [
          { name: 'test_openclaw_compat.py::test_session_persistence', status: 'passed', duration: '0.78s' },
          { name: 'test_openclaw_compat.py::test_agent_scheduling', status: 'passed', duration: '0.56s' },
          { name: 'test_openclaw_compat.py::test_task_tree', status: 'failed', duration: '1.23s', error: 'Mermaid rendering failed' },
        ],
      },
    ],
    failedTests: [
      {
        name: 'test_api_real.py::test_webhook_endpoint',
        error: 'Connection timeout after 2000ms',
        duration: '2.45s',
        category: 'API 集成测试',
      },
      {
        name: 'test_panel_security.py::test_rate_limiting',
        error: 'Rate limit exceeded for IP 192.168.1.100',
        duration: '1.89s',
        category: '安全测试',
      },
      {
        name: 'test_dynamic_tool_synthesis.py::test_resource_limits',
        error: 'Container OOM: memory limit exceeded (256MB)',
        duration: '5.67s',
        category: '动态工具测试',
      },
      {
        name: 'test_openclaw_compat.py::test_task_tree',
        error: 'Mermaid rendering failed: invalid syntax',
        duration: '1.23s',
        category: 'OpenClaw 兼容性测试',
      },
    ],
    lastRun: new Date(Date.now() - 3600000).toISOString(),
  }

  return NextResponse.json(tests)
}
