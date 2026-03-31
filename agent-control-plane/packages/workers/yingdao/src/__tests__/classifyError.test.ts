/**
 * classifyError() 测试
 *
 * 覆盖 8+ 错误场景
 */

import { MockYingdaoWorkerAdapter } from '../adapters/mock';

describe('classifyError', () => {
  let adapter: MockYingdaoWorkerAdapter;

  beforeEach(() => {
    adapter = new MockYingdaoWorkerAdapter();
  });

  test('1. ECONNREFUSED / NETWORK → transient, retryable', () => {
    const error = new Error('ECONNREFUSED');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('transient');
    expect(classification.retryable).toBe(true);
    expect(classification.suggested_action).toBe('retry_with_delay');
    expect(classification.retry_delay_ms).toBe(5000);
    expect(classification.max_retries).toBe(3);
  });

  test('2. AUTH_FAILED → permanent, manual', () => {
    const error = new Error('AUTH_FAILED');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('permanent');
    expect(classification.retryable).toBe(false);
    expect(classification.suggested_action).toBe('manual');
    expect(classification.code).toBe('AUTH_FAILED');
  });

  test('3. FLOW_NOT_FOUND → permanent, manual', () => {
    const error = new Error('FLOW_NOT_FOUND');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('permanent');
    expect(classification.retryable).toBe(false);
    expect(classification.suggested_action).toBe('manual');
    expect(classification.code).toBe('ELEMENT_NOT_FOUND');
  });

  test('4. INVALID_INPUT / VALIDATION → business, manual', () => {
    const error = new Error('VALIDATION_FAILED');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('business');
    expect(classification.retryable).toBe(false);
    expect(classification.suggested_action).toBe('manual');
    expect(classification.code).toBe('VALIDATION_FAILED');
  });

  test('5. ELEMENT_NOT_FOUND → permanent, manual', () => {
    const error = new Error('ELEMENT_NOT_FOUND');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('permanent');
    expect(classification.retryable).toBe(false);
    expect(classification.suggested_action).toBe('manual');
    expect(classification.code).toBe('ELEMENT_NOT_FOUND');
  });

  test('6. TIMEOUT → transient, retryable', () => {
    const error = new Error('TIMEOUT');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('transient');
    expect(classification.retryable).toBe(true);
    expect(classification.suggested_action).toBe('retry_with_delay');
    expect(classification.retry_delay_ms).toBe(5000);
    expect(classification.max_retries).toBe(3);
  });

  test('7. DUPLICATE_RECORD → business, skip', () => {
    const error = new Error('DUPLICATE_RECORD');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('business');
    expect(classification.retryable).toBe(false);
    expect(classification.suggested_action).toBe('skip');
    expect(classification.code).toBe('DUPLICATE_RECORD');
  });

  test('8. ARTIFACT_MISSING / UNKNOWN → system, escalate', () => {
    const error = new Error('ARTIFACT_MISSING');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('system');
    expect(classification.retryable).toBe(false);
    expect(classification.suggested_action).toBe('escalate');
    expect(classification.code).toBe('UNKNOWN_ERROR');
  });

  test('9. NETWORK_ERROR → transient, retryable', () => {
    const error = new Error('NETWORK_ERROR');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('transient');
    expect(classification.retryable).toBe(true);
    expect(classification.suggested_action).toBe('retry_with_delay');
  });

  test('10. ERP_BUSY → transient, retryable', () => {
    const error = new Error('ERP_BUSY');
    const classification = adapter.classifyError(error);

    expect(classification.category).toBe('transient');
    expect(classification.retryable).toBe(true);
    expect(classification.suggested_action).toBe('retry_with_delay');
  });
});
