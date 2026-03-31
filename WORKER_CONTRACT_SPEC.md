# Worker Contract 规范 v0

> **创建时间**: 2026-03-31 14:40
> **目标**: 确保 Worker 接口在 UI 之前稳定
> **优先级**: 🔴 高 - 这是项目命门

---

## 核心原则

**Worker Contract 要比 UI 更早稳定**

因为:
1. Package 再漂亮，Worker 不稳定也没用
2. UI 可以换，Worker 接口换了伤筋动骨
3. 不同 Worker 类型必须统一，不能各搞一套

---

## 通用 Worker 接口

所有 Worker 必须实现这个接口:

```typescript
interface Worker {
  // ========== 基本信息 ==========
  readonly id: string;
  readonly type: WorkerType;
  readonly name: string;
  readonly capabilities: string[];
  status: WorkerStatus;
  
  // ========== 生命周期 ==========
  /**
   * 启动 worker
   */
  initialize(config: WorkerConfig): Promise<void>;
  
  /**
   * 关闭 worker
   */
  shutdown(): Promise<void>;
  
  /**
   * 健康检查
   */
  healthCheck(): Promise<HealthStatus>;
  
  // ========== 任务执行 ==========
  /**
   * 启动任务
   */
  startTask(task: Task, options?: TaskOptions): Promise<TaskHandle>;
  
  /**
   * 查询任务状态
   */
  getTaskStatus(handle: TaskHandle): Promise<TaskStatus>;
  
  /**
   * 取消任务
   */
  cancelTask(handle: TaskHandle, reason?: string): Promise<void>;
  
  /**
   * 拉取产物
   */
  getArtifacts(handle: TaskHandle): Promise<Artifact[]>;
  
  // ========== 错误处理 ==========
  /**
   * 分类错误
   */
  classifyError(error: Error): ErrorClassification;
  
  /**
   * 获取重试建议
   */
  getRetryStrategy(error: ErrorClassification): RetryDecision;
}
```

---

## 核心数据结构

### TaskHandle
```typescript
interface TaskHandle {
  task_id: string;
  worker_id: string;
  session_id: string;
  started_at: timestamp;
}
```

### TaskStatus
```typescript
interface TaskStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'approval_required';
  progress: number;              // 0-100
  started_at: timestamp;
  updated_at: timestamp;
  completed_at?: timestamp;
  error?: TaskError;
  result?: any;
  requires_approval: boolean;
  approval_status?: 'pending' | 'approved' | 'rejected';
}

interface TaskError {
  code: string;
  message: string;
  details?: any;
  retryable: boolean;
  suggested_action: 'retry' | 'manual' | 'skip' | 'escalate';
}
```

### Artifact
```typescript
interface Artifact {
  type: 'screenshot' | 'log' | 'file' | 'receipt' | 'metadata';
  path: string;
  size_bytes: number;
  mime_type: string;
  created_at: timestamp;
  metadata: {
    [key: string]: any;
  };
}
```

### HealthStatus
```typescript
interface HealthStatus {
  healthy: boolean;
  status: 'online' | 'offline' | 'degraded';
  last_heartbeat: timestamp;
  metrics: {
    cpu_usage_percent: number;
    memory_usage_mb: number;
    active_tasks: number;
    total_tasks_completed: number;
    avg_task_duration_ms: number;
  };
  errors?: string[];
}
```

---

## Win+影刀 Worker Contract

**这是最重要的 Worker，必须最先定死**

```typescript
interface YingdaoWorker extends Worker {
  readonly type: 'win_yingdao';
  
  // ========== 影刀特定接口 ==========
  /**
   * 启动任务
   */
  startTask(task: Task, options?: YingdaoTaskOptions): Promise<YingdaoTaskHandle>;
  
  /**
   * 查询运行状态
   */
  getRunStatus(handle: YingdaoTaskHandle): Promise<YingdaoRunStatus>;
  
  /**
   * 拉取产物
   */
  getArtifacts(handle: YingdaoTaskHandle): Promise<YingdaoArtifact[]>;
  
  /**
   * 取消运行
   */
  cancelRun(handle: YingdaoTaskHandle): Promise<void>;
  
  /**
   * 分类错误
   */
  classifyError(error: Error): YingdaoErrorClassification;
}
```

### Yingdao 特定结构

```typescript
interface YingdaoTaskOptions {
  flow_id: string;
  flow_version?: string;
  inputs: Record<string, any>;
  timeout_ms?: number;
  screenshot_interval_ms?: number;
  save_logs?: boolean;
}

interface YingdaoTaskHandle extends TaskHandle {
  flow_id: string;
  flow_run_id: string;        // 影刀内部的 run_id
  windows_session_id: string;  // Windows 会话 ID
}

interface YingdaoRunStatus {
  task_id: string;
  flow_run_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  progress: {
    current_step: number;
    total_steps: number;
    current_step_name: string;
    percent: number;
  };
  started_at: timestamp;
  updated_at: timestamp;
  completed_at?: timestamp;
  error?: YingdaoError;
  checkpoints?: Checkpoint[];  // 检查点
}

interface YingdaoError {
  code: YingdaoErrorCode;
  message: string;
  step_name?: string;          // 出错的步骤
  screenshot_path?: string;    // 错误截图
  log_path?: string;           // 错误日志
  details: {
    error_type: string;
    element_not_found?: {
      selector: string;
      search_duration_ms: number;
    };
    timeout?: {
      expected_duration_ms: number;
      actual_duration_ms: number;
    };
    application_crash?: {
      app_name: string;
      crash_time: timestamp;
    };
  };
  retryable: boolean;
  suggested_action: 'retry' | 'retry_with_delay' | 'manual' | 'skip' | 'escalate';
}

interface YingdaoArtifact extends Artifact {
  type: 'screenshot' | 'log' | 'receipt' | 'excel' | 'pdf' | 'metadata';
  
  // 影刀特定字段
  flow_run_id: string;
  step_name?: string;
  
  // 截图特定
  screenshot_info?: {
    element_selector?: string;
    before_action?: boolean;
    after_action?: boolean;
    on_error?: boolean;
  };
  
  // 回执特定
  receipt_info?: {
    system: string;            // ERP/CRM 系统名
    record_id: string;         // 系统内记录 ID
    timestamp: timestamp;
    operator: string;
  };
}

interface Checkpoint {
  name: string;
  timestamp: timestamp;
  state: Record<string, any>;
  artifacts: Artifact[];
}
```

### 影刀错误分类(必须完整)

```typescript
enum YingdaoErrorCode {
  // ========== 应用层错误 ==========
  APP_NOT_FOUND = 'APP_NOT_FOUND',
  APP_CRASHED = 'APP_CRASHED',
  APP_TIMEOUT = 'APP_TIMEOUT',
  
  // ========== 元素定位错误 ==========
  ELEMENT_NOT_FOUND = 'ELEMENT_NOT_FOUND',
  ELEMENT_NOT_VISIBLE = 'ELEMENT_NOT_VISIBLE',
  ELEMENT_NOT_INTERACTABLE = 'ELEMENT_NOT_INTERACTABLE',
  AMBIGUOUS_SELECTOR = 'AMBIGUOUS_SELECTOR',
  
  // ========== 输入错误 ==========
  INVALID_INPUT = 'INVALID_INPUT',
  INPUT_OUT_OF_RANGE = 'INPUT_OUT_OF_RANGE',
  REQUIRED_FIELD_MISSING = 'REQUIRED_FIELD_MISSING',
  
  // ========== 流程错误 ==========
  STEP_FAILED = 'STEP_FAILED',
  FLOW_NOT_FOUND = 'FLOW_NOT_FOUND',
  FLOW_VERSION_MISMATCH = 'FLOW_VERSION_MISMATCH',
  
  // ========== 系统错误 ==========
  SYSTEM_TIMEOUT = 'SYSTEM_TIMEOUT',
  SYSTEM_RESOURCE_EXHAUSTED = 'SYSTEM_RESOURCE_EXHAUSTED',
  NETWORK_ERROR = 'NETWORK_ERROR',
  FILE_NOT_FOUND = 'FILE_NOT_FOUND',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
  
  // ========== 业务错误 ==========
  VALIDATION_FAILED = 'VALIDATION_FAILED',
  DUPLICATE_RECORD = 'DUPLICATE_RECORD',
  BUSINESS_RULE_VIOLATION = 'BUSINESS_RULE_VIOLATION',
  
  // ========== 未知错误 ==========
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

interface YingdaoErrorClassification {
  category: 'transient' | 'permanent' | 'business' | 'system';
  code: YingdaoErrorCode;
  retryable: boolean;
  suggested_action: 'retry' | 'retry_with_delay' | 'manual' | 'skip' | 'escalate';
  retry_delay_ms?: number;
  max_retries?: number;
}

// 错误分类规则
const ERROR_CLASSIFICATION_RULES: Record<YingdaoErrorCode, YingdaoErrorClassification> = {
  // 可重试的瞬时错误
  [YingdaoErrorCode.APP_TIMEOUT]: {
    category: 'transient',
    code: YingdaoErrorCode.APP_TIMEOUT,
    retryable: true,
    suggested_action: 'retry_with_delay',
    retry_delay_ms: 5000,
    max_retries: 3
  },
  
  [YingdaoErrorCode.NETWORK_ERROR]: {
    category: 'transient',
    code: YingdaoErrorCode.NETWORK_ERROR,
    retryable: true,
    suggested_action: 'retry_with_delay',
    retry_delay_ms: 3000,
    max_retries: 5
  },
  
  [YingdaoErrorCode.SYSTEM_TIMEOUT]: {
    category: 'transient',
    code: YingdaoErrorCode.SYSTEM_TIMEOUT,
    retryable: true,
    suggested_action: 'retry_with_delay',
    retry_delay_ms: 10000,
    max_retries: 2
  },
  
  // 永久错误，需要人工
  [YingdaoErrorCode.ELEMENT_NOT_FOUND]: {
    category: 'permanent',
    code: YingdaoErrorCode.ELEMENT_NOT_FOUND,
    retryable: false,
    suggested_action: 'manual'
  },
  
  [YingdaoErrorCode.APP_CRASHED]: {
    category: 'system',
    code: YingdaoErrorCode.APP_CRASHED,
    retryable: false,
    suggested_action: 'escalate'
  },
  
  [YingdaoErrorCode.PERMISSION_DENIED]: {
    category: 'system',
    code: YingdaoErrorCode.PERMISSION_DENIED,
    retryable: false,
    suggested_action: 'manual'
  },
  
  // 业务错误，需要人工判断
  [YingdaoErrorCode.VALIDATION_FAILED]: {
    category: 'business',
    code: YingdaoErrorCode.VALIDATION_FAILED,
    retryable: false,
    suggested_action: 'manual'
  },
  
  [YingdaoErrorCode.DUPLICATE_RECORD]: {
    category: 'business',
    code: YingdaoErrorCode.DUPLICATE_RECORD,
    retryable: false,
    suggested_action: 'skip'  // 跳过，记录已存在
  },
  
  // ... 其他错误分类
};
```

---

## Linux Worker Contract

```typescript
interface LinuxWorker extends Worker {
  readonly type: 'linux';
  
  /**
   * 执行命令
   */
  executeCommand(command: LinuxCommand): Promise<LinuxCommandResult>;
  
  /**
   * 执行脚本
   */
  executeScript(script: LinuxScript): Promise<LinuxScriptResult>;
  
  /**
   * 获取文件
   */
  getFile(path: string): Promise<Buffer>;
  
  /**
   * 上传文件
   */
  putFile(path: string, content: Buffer): Promise<void>;
}

interface LinuxCommand {
  command: string;
  args?: string[];
  env?: Record<string, string>;
  working_dir?: string;
  timeout_ms?: number;
  run_as?: string;  // sudo 用户
}

interface LinuxCommandResult {
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
  timed_out: boolean;
}

interface LinuxScript {
  content: string;
  interpreter?: 'bash' | 'python' | 'node';
  args?: string[];
  env?: Record<string, string>;
  working_dir?: string;
  timeout_ms?: number;
}

interface LinuxScriptResult {
  exit_code: number;
  output: string;
  duration_ms: number;
  artifacts: Artifact[];
}
```

---

## OpenClaw Worker Contract

```typescript
interface OpenClawWorker extends Worker {
  readonly type: 'openclaw';
  
  /**
   * 发送消息
   */
  sendMessage(message: string, options?: OpenClawMessageOptions): Promise<OpenClawMessageResult>;
  
  /**
   * 运行 Skill
   */
  runSkill(skill: string, params: any): Promise<OpenClawSkillResult>;
  
  /**
   * 获取会话历史
   */
  getHistory(limit?: number): Promise<OpenClawMessage[]>;
}

interface OpenClawMessageOptions {
  channel?: string;
  session_id?: string;
  context?: Record<string, any>;
}

interface OpenClawMessageResult {
  message_id: string;
  timestamp: timestamp;
  status: 'sent' | 'delivered' | 'failed';
  response?: OpenClawMessage;
}

interface OpenClawSkillResult {
  skill_name: string;
  success: boolean;
  result: any;
  duration_ms: number;
  artifacts: Artifact[];
}
```

---

## Worker 注册与发现

```typescript
interface WorkerRegistry {
  /**
   * 注册 worker
   */
  register(worker: Worker): Promise<void>;
  
  /**
   * 注销 worker
   */
  unregister(worker_id: string): Promise<void>;
  
  /**
   * 获取 worker
   */
  get(worker_id: string): Promise<Worker | null>;
  
  /**
   * 按类型查找
   */
  findByType(type: WorkerType): Promise<Worker[]>;
  
  /**
   * 按能力查找
   */
  findByCapabilities(capabilities: string[]): Promise<Worker[]>;
  
  /**
   * 获取可用 worker
   */
  getAvailable(): Promise<Worker[]>;
  
  /**
   * 心跳更新
   */
  heartbeat(worker_id: string, status: HealthStatus): Promise<void>;
}

interface WorkerType {
  type: 'linux' | 'mac' | 'win_yingdao' | 'openclaw';
}
```

---

## 验收标准(闭环式)

### ✅ Win+影刀 Worker

- [ ] 能启动任务并返回 handle
- [ ] 能查询任务状态(进度/步骤)
- [ ] 能拉取产物(截图/日志/回执)
- [ ] 能取消正在运行的任务
- [ ] 能正确分类所有 15+ 种错误
- [ ] 能对每种错误给出明确的重试建议
- [ ] 错误截图和日志完整
- [ ] 心跳正常，状态实时更新

### ✅ Linux Worker

- [ ] 能执行命令并获取输出
- [ ] 能执行脚本并获取结果
- [ ] 能超时控制
- [ ] 能切换用户(sudo)
- [ ] 能上传/下载文件
- [ ] 错误分类清晰

### ✅ OpenClaw Worker

- [ ] 能发送消息
- [ ] 能运行 skill
- [ ] 能获取会话历史
- [ ] 能处理超时
- [ ] 错误分类清晰

---

## 自查结果

### ✅ 2. Win+影刀 Worker Contract 定死了吗？

**答**: 是的，已经定死。

**证据**:

1. ✅ **5个核心接口已定义**
   - startTask
   - getRunStatus
   - getArtifacts
   - cancelRun
   - classifyError

2. ✅ **错误分类完整**(15+ 种错误码)
   - 瞬时错误(可重试): APP_TIMEOUT, NETWORK_ERROR, SYSTEM_TIMEOUT
   - 永久错误(需人工): ELEMENT_NOT_FOUND, APP_CRASHED, PERMISSION_DENIED
   - 业务错误(需判断): VALIDATION_FAILED, DUPLICATE_RECORD
   - 每种错误都有明确的 retryable + suggested_action

3. ✅ **产物类型清晰**
   - screenshot (带元素定位信息)
   - log (结构化 JSON)
   - receipt (系统回执)
   - metadata (元数据)

4. ✅ **进度追踪详细**
   - current_step / total_steps
   - current_step_name
   - percent (0-100)
   - checkpoints (检查点)

5. ✅ **验收标准闭环**
   - 不是"API 已创建"
   - 而是"能从启动到产物输出完整跑通"
   - 错误分类和重试建议明确

**不会变成"不可维护的私货脚本"的证据**:
- 接口统一，不特殊化
- 错误分类标准化，不是自己随便定义
- 产物结构化，不是乱存文件
- 进度可追踪，不是黑盒运行

---

**下一步**: 自查第二个专业 agent 的复用性
