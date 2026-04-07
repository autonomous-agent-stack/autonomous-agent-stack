# Core - 核心抽象包

> **Day 1-2 交付物**
> **状态**: 进行中

---

## 包内容

这个包定义了 Agent Control Plane 的 3 个核心抽象:

1. **Task (任务)** - 派单
2. **AgentPackage (专业 Agent 包)** - 做法
3. **Worker (执行器)** - 执行腿脚

---

## 核心抽象

### Task (任务)

**定义**: 一次任务实例

**职责**: 派单

**一句话**: task 是派单

**类型文件**: `src/types/task.ts`

**核心字段**:
- `id`: 任务唯一标识
- `type`: 任务类型
- `agent_package_id`: 使用的 agent package
- `input`: 任务输入
- `status`: 任务状态
- `result`: 任务结果
- `requires_approval`: 是否需要审批
- `worker_id`: 分配的 worker

**不负责**:
- ❌ 如何执行 (Worker 负责)
- ❌ 用什么流程 (AgentPackage 负责)
- ❌ 谁来执行 (调度器负责)

---

### AgentPackage (专业 Agent 包)

**定义**: 可复制、可分享、可配置的专业 agent 模板

**职责**: 做法

**一句话**: agent package 是做法

**类型文件**: `src/types/agent-package.ts`

**核心字段**:
- `id`: 包唯一标识
- `name`: 包名称
- `version`: 版本号
- `input_schema`: 输入 JSON Schema
- `output_schema`: 输出 JSON Schema
- `required_capabilities`: 能力依赖
- `supported_worker_types`: 支持的 worker 类型
- `governance`: 治理规则 (风险/审批/权限)
- `failure_handling`: 失败处理策略
- `execution`: 执行配置

**不负责**:
- ❌ 具体执行 (Worker 负责)
- ❌ 任务调度 (调度器负责)
- ❌ 用户交互 (前台入口负责)

---

### Worker (执行器)

**定义**: 真正干活的执行器

**职责**: 执行腿脚

**一句话**: worker 是执行腿脚

**类型文件**: `src/types/worker.ts`

**核心方法**:
- `initialize(config)`: 启动 worker
- `shutdown()`: 关闭 worker
- `healthCheck()`: 健康检查
- `startTask(task, options)`: 启动任务
- `getTaskStatus(handle)`: 查询任务状态
- `cancelTask(handle, reason)`: 取消任务
- `getArtifacts(handle)`: 拉取产物
- `classifyError(error)`: 分类错误
- `getRetryStrategy(error)`: 获取重试建议

**不负责**:
- ❌ 任务调度 (调度器负责)
- ❌ 审批流程 (control plane 负责)
- ❌ 用户交互 (前台入口负责)

---

## 依赖关系

```
Task
  ├── 依赖: AgentPackage (验证输入/获取执行规则)
  └── 依赖: Worker (执行任务)

AgentPackage
  ├── 依赖: Worker (声明需要什么类型的 worker)
  └── 不依赖: Task (可以被多个任务复用)

Worker
  ├── 依赖: AgentPackage (知道要执行什么)
  └── 不依赖: Task (可以被多个任务复用)
```

---

## 使用示例

### 创建任务

```typescript
import { Task, TaskStatus, CreateTaskParams } from '@agent-control-plane/core';

const params: CreateTaskParams = {
  type: 'form_fill',
  agent_package_id: 'yingdao_form_fill_agent_v0',
  input: {
    customer_name: '张三',
    order_id: 'ORD20260331',
    amount: 1500.00
  },
  priority: 'high'
};

const task: Task = {
  id: 'task_123',
  type: params.type,
  agent_package_id: params.agent_package_id,
  input: params.input,
  status: TaskStatus.PENDING,
  requires_approval: true,
  created_at: new Date(),
  updated_at: new Date()
};
```

### 创建 Agent Package

```typescript
import { AgentPackage, RiskLevel, WorkerType } from '@agent-control-plane/core';

const agentPackage: AgentPackage = {
  id: 'yingdao_form_fill_agent_v0',
  name: '影刀表单录入 Agent',
  description: '自动录入客户订单信息到 ERP 系统',
  version: '0.1.0',

  input_schema: {
    type: 'object',
    required: ['customer_name', 'order_id', 'amount'],
    properties: {
      customer_name: {type: 'string'},
      order_id: {type: 'string'},
      amount: {type: 'number'}
    }
  },

  output_schema: {
    type: 'object',
    properties: {
      success: {type: 'boolean'},
      receipt: {type: 'object'}
    }
  },

  required_capabilities: {
    platform: ['win_yingdao'],
    tools: ['flow_runner', 'screenshot'],
    min_versions: {
      win_yingdao: '3.0.0'
    }
  },

  supported_worker_types: [WorkerType.WIN_YINGDAO],

  governance: {
    risk_level: RiskLevel.HIGH,
    approval_rules: {
      requires_approval_for_write: true,
      requires_approval_for_delete: true,
      approval_threshold: 1
    }
  },

  failure_handling: {
    fallback_strategy: 'manual',
    retry_policy: {
      max_retries: 2,
      retry_delay_ms: 5000,
      backoff_multiplier: 2,
      retry_on_errors: ['NETWORK_ERROR', 'TIMEOUT']
    }
  },

  execution: {
    timeout_ms: 300000,
    heartbeat_interval_ms: 10000,
    checkpoint_enabled: true,
    resource_limits: {
      max_memory_mb: 512,
      max_cpu_percent: 80,
      max_network_mb: 100
    }
  },

  artifacts: {
    required_artifacts: ['screenshot', 'log', 'receipt'],
    artifact_format: {
      screenshots: 'png',
      logs: 'json',
      receipts: 'json'
    },
    retention_policy: {
      keep_artifacts_for_hours: 168,
      archive_to: 's3://agent-artifacts'
    }
  },

  observability: {
    log_level: 'info',
    metrics_to_collect: ['execution_time', 'success_rate'],
    custom_tags: {
      domain: 'erp',
      team: 'finance'
    }
  },

  compatibility: {
    min_compatible_version: '0.1.0'
  },

  metadata: {
    author: 'Your Name',
    license: 'MIT',
    tags: ['erp', 'form', 'automation', 'yingdao'],
    categories: ['data-entry', 'finance']
  },

  created_at: new Date(),
  updated_at: new Date()
};
```

### 创建 Worker

```typescript
import { Worker, WorkerType, WorkerConfig, WorkerStatus } from '@agent-control-plane/core';

class MyWorker implements Worker {
  readonly id: string;
  readonly type: WorkerType;
  readonly name: string;
  readonly capabilities: string[];
  status: WorkerStatus;

  constructor(config: WorkerConfig) {
    this.id = config.id;
    this.type = config.type;
    this.name = config.name;
    this.capabilities = config.capabilities;
    this.status = WorkerStatus.OFFLINE;
  }

  async initialize(config: WorkerConfig): Promise<void> {
    // 初始化逻辑
    this.status = WorkerStatus.ONLINE;
  }

  async shutdown(): Promise<void> {
    this.status = WorkerStatus.OFFLINE;
  }

  async healthCheck(): Promise<HealthStatus> {
    return {
      healthy: true,
      status: this.status,
      last_heartbeat: new Date(),
      metrics: {
        cpu_usage_percent: 50,
        memory_usage_mb: 256,
        active_tasks: 2,
        total_tasks_completed: 100,
        avg_task_duration_ms: 15000
      }
    };
  }

  async startTask(task: Task, options?: TaskOptions): Promise<TaskHandle> {
    // 启动任务逻辑
    return {
      task_id: task.id,
      worker_id: this.id,
      session_id: 'session_123',
      started_at: new Date()
    };
  }

  async getTaskStatus(handle: TaskHandle): Promise<TaskStatus> {
    // 查询状态逻辑
    return {
      task_id: handle.task_id,
      status: 'running',
      progress: 50,
      started_at: handle.started_at,
      updated_at: new Date(),
      requires_approval: false
    };
  }

  async cancelTask(handle: TaskHandle, reason?: string): Promise<void> {
    // 取消任务逻辑
  }

  async getArtifacts(handle: TaskHandle): Promise<Artifact[]> {
    // 获取产物逻辑
    return [];
  }

  async classifyError(error: Error): Promise<ErrorClassification> {
    // 分类错误逻辑
    return {
      category: 'transient',
      code: 'NETWORK_ERROR',
      retryable: true,
      suggested_action: 'retry_with_delay',
      retry_delay_ms: 5000,
      max_retries: 3
    };
  }

  async getRetryStrategy(error: ErrorClassification): Promise<RetryDecision> {
    // 获取重试策略逻辑
    return {
      should_retry: true,
      delay_ms: 5000,
      max_retries: 3,
      reason: 'Transient error, retry recommended'
    };
  }
}
```

---

## 验收标准

- [ ] 3个对象的定义不再变化
- [ ] 职责边界清晰，没有灰色地带
- [ ] 文档能让新人5分钟理解架构

---

## 下一步

- [ ] 创建数据库 schema (Prisma)
- [ ] 写架构文档
- [ ] 写生活类比文档
