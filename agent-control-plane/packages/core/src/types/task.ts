/**
 * Task - 任务类型定义
 *
 * 定义: 一次任务实例
 * 职责: 派单
 * 一句话: task 是派单
 */

/**
 * 任务状态
 */
export enum TaskStatus {
  PENDING = 'pending',              // 待处理
  RUNNING = 'running',              // 运行中
  COMPLETED = 'completed',          // 已完成
  FAILED = 'failed',                // 已失败
  CANCELLED = 'cancelled',          // 已取消
  APPROVAL_REQUIRED = 'approval_required',  // 需要审批
}

/**
 * 审批状态
 */
export enum ApprovalStatus {
  PENDING = 'pending',              // 待审批
  APPROVED = 'approved',            // 已批准
  REJECTED = 'rejected',            // 已拒绝
}

/**
 * 任务输入
 */
export interface TaskInput {
  [key: string]: any;
}

/**
 * 任务结果
 */
export interface TaskResult {
  success: boolean;
  data?: any;
  artifacts?: Artifact[];
  completed_at?: Date;
}

/**
 * 产物
 */
export interface Artifact {
  type: 'screenshot' | 'log' | 'file' | 'receipt' | 'metadata';
  path: string;
  size_bytes: number;
  mime_type: string;
  created_at: Date;
  metadata: Record<string, any>;
}

/**
 * 任务错误
 */
export interface TaskError {
  code: string;
  message: string;
  details?: any;
  retryable: boolean;
  suggested_action: 'retry' | 'manual' | 'skip' | 'escalate';
  occurred_at: Date;
}

/**
 * 任务
 */
export interface Task {
  // 基本信息
  id: string;
  type: string;                     // 对应 agent package 类型
  agent_package_id: string;         // 使用的 agent package

  // 输入输出
  input: TaskInput;
  result?: TaskResult;

  // 状态
  status: TaskStatus;

  // 审批
  requires_approval: boolean;
  approval_status?: ApprovalStatus;
  approvers?: string[];

  // 执行
  worker_id?: string;               // 分配的 worker
  started_at?: Date;
  completed_at?: Date;
  timeout_at?: Date;

  // 错误
  error?: TaskError;
  retry_count?: number;
  max_retries?: number;

  // 元数据
  created_at: Date;
  updated_at: Date;
  created_by?: string;              // 创建者
  tags?: string[];
  priority?: 'low' | 'medium' | 'high' | 'critical';
}

/**
 * 任务创建参数
 */
export interface CreateTaskParams {
  type: string;
  agent_package_id: string;
  input: TaskInput;
  created_by?: string;
  priority?: Task['priority'];
  tags?: string[];
}

/**
 * 任务更新参数
 */
export interface UpdateTaskParams {
  status?: TaskStatus;
  worker_id?: string;
  result?: TaskResult;
  error?: TaskError;
  approval_status?: ApprovalStatus;
  retry_count?: number;
}

/**
 * 任务查询参数
 */
export interface QueryTasksParams {
  status?: TaskStatus;
  agent_package_id?: string;
  worker_id?: string;
  created_by?: string;
  priority?: Task['priority'];
  tags?: string[];
  created_after?: Date;
  created_before?: Date;
  limit?: number;
  offset?: number;
}
