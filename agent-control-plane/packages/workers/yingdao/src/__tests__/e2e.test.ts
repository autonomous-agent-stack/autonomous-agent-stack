/**
 * E2E 测试 - Mock Worker 完整流程
 */

import { MockYingdaoWorkerAdapter } from '../adapters/mock';
import { Task, TaskStatus } from '@agent-control-plane/core';

describe('E2E: Mock Worker', () => {
  let adapter: MockYingdaoWorkerAdapter;

  beforeEach(() => {
    adapter = new MockYingdaoWorkerAdapter();
  });

  test('完整执行流程: 创建 → 启动 → 轮询 → 产物 → 完成', async () => {
    // 1. 创建任务
    const task: Task = {
      id: 'task-001',
      type: 'form_fill',
      agent_package_id: 'yingdao_form_fill_agent_v0',
      input: {
        customer_name: '张三',
        order_id: 'ORD20260331',
        amount: 1500.00
      },
      status: TaskStatus.PENDING,
      requires_approval: false,
      created_at: new Date(),
      updated_at: new Date()
    };

    // 2. 启动任务
    const handle = await adapter.startTask(task, {
      flow_id: 'form_fill_flow_v1',
      inputs: task.input
    });

    expect(handle.task_id).toBe('task-001');
    expect(handle.flow_run_id).toBeDefined();
    expect(handle.windows_session_id).toBe('mock-session');

    // 3. 轮询状态直到完成
    let completed = false;
    let attempts = 0;
    const maxAttempts = 10;

    while (!completed && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 1500)); // 等待 1.5 秒

      const status = await adapter.getRunStatus(handle);

      // 检查进度
      expect(status.progress.percent).toBeGreaterThanOrEqual(0);
      expect(status.progress.percent).toBeLessThanOrEqual(100);
      expect(status.progress.current_step_name).toBeDefined();

      if (status.status === 'completed') {
        completed = true;
        expect(status.progress.percent).toBe(100);
      } else if (status.status === 'failed' || status.status === 'cancelled') {
        throw new Error(`Task ${status.status}: ${status.error?.message}`);
      }

      attempts++;
    }

    expect(completed).toBe(true);

    // 4. 获取产物 (应该是 4 个)
    const artifacts = await adapter.getArtifacts(handle);
    expect(artifacts).toHaveLength(4);

    // 验证产物类型
    const artifactTypes = artifacts.map(a => a.type);
    expect(artifactTypes).toContain('log');
    expect(artifactTypes).toContain('metadata');  // summary
    expect(artifactTypes).toContain('screenshot');
    expect(artifactTypes).toContain('receipt');

    // 验证 log 产物
    const logArtifact = artifacts.find(a => a.type === 'log');
    expect(logArtifact).toBeDefined();
    expect(logArtifact?.mime_type).toBe('application/json');
    expect(logArtifact?.path).toContain('.log');

    // 验证 metadata 产物
    const metadataArtifact = artifacts.find(a => a.type === 'metadata');
    expect(metadataArtifact).toBeDefined();
    expect(metadataArtifact?.mime_type).toBe('application/json');
    expect(metadataArtifact?.path).toContain('summary');

    // 验证 screenshot 产物
    const screenshotArtifact = artifacts.find(a => a.type === 'screenshot');
    expect(screenshotArtifact).toBeDefined();
    expect(screenshotArtifact?.mime_type).toBe('image/png');
    expect(screenshotArtifact?.screenshot_info?.after_action).toBe(true);

    // 验证 receipt 产物
    const receiptArtifact = artifacts.find(a => a.type === 'receipt');
    expect(receiptArtifact).toBeDefined();
    expect(receiptArtifact?.receipt_info).toBeDefined();
    expect(receiptArtifact?.receipt_info?.system).toBe('MOCK_ERP');
    expect(receiptArtifact?.receipt_info?.record_id).toBeDefined();
  });

  test('取消任务流程', async () => {
    // 1. 创建并启动任务
    const task: Task = {
      id: 'task-002',
      type: 'form_fill',
      agent_package_id: 'yingdao_form_fill_agent_v0',
      input: {
        customer_name: '李四',
        order_id: 'ORD20260332',
        amount: 2000.00
      },
      status: TaskStatus.PENDING,
      requires_approval: false,
      created_at: new Date(),
      updated_at: new Date()
    };

    const handle = await adapter.startTask(task, {
      flow_id: 'form_fill_flow_v1',
      inputs: task.input
    });

    // 2. 立即取消
    await adapter.cancelRun(handle, '测试取消');

    // 3. 验证状态已取消
    const status = await adapter.getRunStatus(handle);
    expect(status.status).toBe('cancelled');
    expect(status.completed_at).toBeDefined();
  });

  test('错误分类: 10 种场景', () => {
    const errorScenarios = [
      { error: new Error('ECONNREFUSED'), category: 'transient', retryable: true },
      { error: new Error('AUTH_FAILED'), category: 'permanent', retryable: false },
      { error: new Error('FLOW_NOT_FOUND'), category: 'permanent', retryable: false },
      { error: new Error('VALIDATION_FAILED'), category: 'business', retryable: false },
      { error: new Error('ELEMENT_NOT_FOUND'), category: 'permanent', retryable: false },
      { error: new Error('TIMEOUT'), category: 'transient', retryable: true },
      { error: new Error('DUPLICATE_RECORD'), category: 'business', retryable: false },
      { error: new Error('ARTIFACT_MISSING'), category: 'system', retryable: false },
      { error: new Error('NETWORK_ERROR'), category: 'transient', retryable: true },
      { error: new Error('ERP_BUSY'), category: 'transient', retryable: true }
    ];

    errorScenarios.forEach(({ error, category, retryable }) => {
      const classification = adapter.classifyError(error);
      expect(classification.category).toBe(category);
      expect(classification.retryable).toBe(retryable);
    });
  });
});
