# Day 3-4: 影刀执行底座

> **分支**: feature/control-plane-v0-sprint18
> **时间**: 2026-03-31 15:30
> **目标**: 先用 mock 跑通闭环，再逐步接真影刀

---

## 3个强约束

### 1. 假实现可跑 + 真实现占位

**两层架构**:
```
WinYingdaoWorkerContract (接口)
  ├── MockYingdaoWorkerAdapter (假实现，可跑)
  └── RealYingdaoWorkerAdapter (真实现，占位)
```

**好处**:
- Day 3-4 不会因外部环境卡死
- 能先验证 contract 可行性
- 逐步替换真影刀接入

---

### 2. classifyError() 必须先写测试

**这是命门**，因为 retry/fallback/needs_review 都靠它。

**必须测试的错误场景** (至少7个):
- [ ] 连接失败
- [ ] 登录失效
- [ ] flow 不存在
- [ ] 输入校验失败
- [ ] 页面元素缺失
- [ ] 超时
- [ ] ERP 业务拒绝
- [ ] 产物缺失

**测试先行**:
```bash
# 先写测试
npm test -- classifyError.test.ts

# 测试通过后再实现
# 实现
```

---

### 3. 产物结构先定"最小必需集"

**Day 3-4 只强制要求**:
- `run.log` - 运行日志 (JSON 格式)
- `summary.json` - 执行摘要
- `final_screenshot.png` - 最终截图
- `receipt.json` - 业务回执

**不加**:
- ❌ 录屏
- ❌ 全量中间截图
- ❌ 复杂 trace

**原因**: 先跑通，不加重实现

---

## 今日目标

### 核心任务
- [ ] 实现 WinYingdaoWorkerContract 接口
- [ ] 实现 MockYingdaoWorkerAdapter
- [ ] 实现 RealYingdaoWorkerAdapter (占位)
- [ ] 写 classifyError() 的完整测试
- [ ] 定义最小产物结构
- [ ] 跑通第一个 end-to-end 测试

### 验收标准
- [ ] Mock adapter 能跑通 contract
- [ ] classifyError() 测试覆盖 7+ 场景
- [ ] 产物结构只有 4 个文件
- [ ] E2E 测试通过

---

## 实现计划

### Step 1: 实现 Contract 接口

```typescript
// packages/workers/yingdao/src/contract.ts
export interface WinYingdaoWorkerContract {
  startTask(task: Task, options: YingdaoTaskOptions): Promise<YingdaoTaskHandle>;
  getRunStatus(handle: YingdaoTaskHandle): Promise<YingdaoRunStatus>;
  getArtifacts(handle: YingdaoTaskHandle): Promise<YingdaoArtifact[]>;
  cancelRun(handle: YingdaoTaskHandle): Promise<void>;
  classifyError(error: Error): YingdaoErrorClassification;
}
```

---

### Step 2: 实现 Mock Adapter

```typescript
// packages/workers/yingdao/src/adapters/mock.ts
export class MockYingdaoWorkerAdapter implements WinYingdaoWorkerContract {
  async startTask(task, options) {
    // 模拟启动
    return {
      task_id: task.id,
      worker_id: 'mock-worker',
      flow_run_id: 'mock-run-123',
      windows_session_id: 'mock-session',
      started_at: new Date()
    };
  }

  async getRunStatus(handle) {
    // 模拟进度
    return {
      task_id: handle.task_id,
      flow_run_id: handle.flow_run_id,
      status: 'running',
      progress: {
        current_step: 2,
        total_steps: 5,
        current_step_name: '填写表单',
        percent: 40
      },
      started_at: handle.started_at,
      updated_at: new Date()
    };
  }

  async getArtifacts(handle) {
    // 模拟产物
    return [
      {
        type: 'log',
        path: '/artifacts/mock-run.log',
        size_bytes: 1024,
        mime_type: 'application/json',
        created_at: new Date(),
        metadata: {}
      },
      {
        type: 'screenshot',
        path: '/artifacts/mock-final.png',
        size_bytes: 204800,
        mime_type: 'image/png',
        created_at: new Date(),
        metadata: {}
      },
      {
        type: 'receipt',
        path: '/artifacts/mock-receipt.json',
        size_bytes: 512,
        mime_type: 'application/json',
        created_at: new Date(),
        metadata: {}
      }
    ];
  }

  async cancelRun(handle, reason) {
    // 模拟取消
    console.log(`Cancelled ${handle.flow_run_id}: ${reason}`);
  }

  async classifyError(error) {
    // 模拟错误分类
    return {
      category: 'transient',
      code: 'MOCK_ERROR',
      retryable: true,
      suggested_action: 'retry_with_delay',
      retry_delay_ms: 5000,
      max_retries: 3
    };
  }
}
```

---

### Step 3: 实现 Real Adapter (占位)

```typescript
// packages/workers/yingdao/src/adapters/real.ts
export class RealYingdaoWorkerAdapter implements WinYingdaoWorkerContract {
  private apiClient: YingdaoApiClient;

  constructor(config: YingdaoWorkerConfig) {
    this.apiClient = new YingdaoApiClient(config);
  }

  async startTask(task, options) {
    // TODO: 接真实影刀 API
    throw new Error('Not implemented yet');
  }

  async getRunStatus(handle) {
    // TODO: 接真实影刀 API
    throw new Error('Not implemented yet');
  }

  async getArtifacts(handle) {
    // TODO: 接真实影刀 API
    throw new Error('Not implemented yet');
  }

  async cancelRun(handle, reason) {
    // TODO: 接真实影刀 API
    throw new Error('Not implemented yet');
  }

  async classifyError(error) {
    // TODO: 实现真实错误分类
    throw new Error('Not implemented yet');
  }
}
```

---

### Step 4: classifyError() 测试

```typescript
// packages/workers/yingdao/src/__tests__/classifyError.test.ts
import { classifyError } from '../classifiers';

describe('classifyError', () => {
  test('连接失败 → transient, retryable', () => {
    const error = new Error('ECONNREFUSED');
    const classification = classifyError(error);
    
    expect(category).toBe('transient');
    expect(retryable).toBe(true);
    expect(suggested_action).toBe('retry_with_delay');
  });

  test('登录失效 → permanent, manual', () => {
    const error = new Error('AUTH_FAILED');
    const classification = classifyError(error);
    
    expect(category).toBe('permanent');
    expect(retryable).toBe(false);
    expect(suggested_action).toBe('manual');
  });

  test('flow 不存在 → permanent, manual', () => {
    const error = new Error('FLOW_NOT_FOUND');
    const classification = classifyError(error);
    
    expect(category).toBe('permanent');
    expect(retryable).toBe(false);
    expect(suggested_action).toBe('manual');
  });

  test('输入校验失败 → business, manual', () => {
    const error = new Error('INVALID_INPUT');
    const classification = classifyError(error);
    
    expect(category).toBe('business');
    expect(retryable).toBe(false);
    expect(suggested_action).toBe('manual');
  });

  test('页面元素缺失 → permanent, manual', () => {
    const error = new Error('ELEMENT_NOT_FOUND');
    const classification = classifyError(error);
    
    expect(category).toBe('permanent');
    expect(retryable).toBe(false);
    expect(suggested_action).toBe('manual');
  });

  test('超时 → transient, retryable', () => {
    const error = new Error('TIMEOUT');
    const classification = classifyError(error);
    
    expect(category).toBe('transient');
    expect(retryable).toBe(true);
    expect(suggested_action).toBe('retry_with_delay');
  });

  test('ERP 业务拒绝 → business, skip', () => {
    const error = new Error('DUPLICATE_RECORD');
    const classification = classifyError(error);
    
    expect(category).toBe('business');
    expect(retryable).toBe(false);
    expect(suggested_action).toBe('skip');
  });

  test('产物缺失 → system, escalate', () => {
    const error = new Error('ARTIFACT_MISSING');
    const classification = classifyError(error);
    
    expect(category).toBe('system');
    expect(retryable).toBe(false);
    expect(suggested_action).toBe('escalate');
  });
});
```

---

### Step 5: 最小产物结构

```typescript
// packages/workers/yingdao/src/artifacts.ts
export interface MinimalArtifacts {
  // 必需
  run_log: RunLog;
  summary: Summary;
  final_screenshot: Screenshot;
  receipt: Receipt;
}

export interface RunLog {
  version: '1.0';
  task_id: string;
  flow_run_id: string;
  started_at: string;
  completed_at: string;
  status: 'success' | 'failed';
  steps: LogEntry[];
}

export interface Summary {
  task_id: string;
  flow_id: string;
  success: boolean;
  duration_ms: number;
  error?: string;
  artifacts_count: number;
}

export interface Screenshot {
  path: string;
  size_bytes: number;
  taken_at: string;
  context: 'before' | 'after' | 'error' | 'final';
}

export interface Receipt {
  system: string;
  record_id: string;
  timestamp: string;
  operator: string;
  data?: Record<string, any>;
}
```

---

### Step 6: E2E 测试

```typescript
// packages/workers/yingdao/src/__tests__/e2e.test.ts
import { MockYingdaoWorkerAdapter } from '../adapters/mock';
import { Task } from '@agent-control-plane/core';

describe('E2E: Mock Worker', () => {
  test('完整执行流程', async () => {
    const worker = new MockYingdaoWorkerAdapter();
    
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
      status: 'pending',
      requires_approval: false,
      created_at: new Date(),
      updated_at: new Date()
    };

    // 2. 启动任务
    const handle = await worker.startTask(task, {
      flow_id: 'form_fill_flow_v1',
      inputs: task.input
    });
    expect(handle.task_id).toBe('task-001');

    // 3. 查询状态
    const status = await worker.getRunStatus(handle);
    expect(status.status).toBe('running');
    expect(status.progress.percent).toBeGreaterThan(0);

    // 4. 获取产物
    const artifacts = await worker.getArtifacts(handle);
    expect(artifacts).toHaveLength(3); // log + screenshot + receipt
    expect(artifacts[0].type).toBe('log');
    expect(artifacts[1].type).toBe('screenshot');
    expect(artifacts[2].type).toBe('receipt');

    // 5. 取消任务
    await worker.cancelRun(handle, '测试取消');
  });
});
```

---

## 验收检查清单

### 接口实现
- [ ] WinYingdaoWorkerContract 接口定义
- [ ] MockYingdaoWorkerAdapter 完整实现
- [ ] RealYingdaoWorkerAdapter 占位实现

### 错误分类
- [ ] classifyError() 方法实现
- [ ] 7+ 错误场景测试
- [ ] 所有测试通过

### 产物结构
- [ ] 只定义 4 个必需产物
- [ ] 每个产物都有明确的 schema
- [ ] Mock adapter 能生成这些产物

### E2E 测试
- [ ] 完整执行流程测试
- [ ] 测试覆盖所有方法
- [ ] 测试通过

---

## 成功标准

**Day 3-4 完成**:
- ✅ 不是"接了真影刀"
- ✅ 而是"contract 可验证"

**具体说**:
- 能用 mock 跑通完整流程
- 错误分类有完整测试覆盖
- 产物结构清晰简洁
- 真影刀接入有占位

---

## 下一步

### Day 5-6 开始前
- [ ] Mock adapter 稳定
- [ ] classifyError() 测试覆盖完整
- [ ] 产物结构验证通过
- [ ] 准备接真实影刀 API

### 真影刀接入
- [ ] 研究 Yingdao API
- [ ] 实现 RealYingdaoWorkerAdapter
- [ ] 逐步替换 mock
- [ ] 增加集成测试

---

## 一句话

**不是直接猛接真实影刀，而是先用 mock adapter 跑通 contract，再逐步接真影刀。**

**目标**: 做成第一个"协议落地到执行"的硬闭环。
