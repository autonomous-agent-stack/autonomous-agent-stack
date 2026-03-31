/**
 * Worker - 执行器类型定义
 *
 * 定义: 真正干活的执行器
 * 职责: 执行腿脚
 * 一句话: worker 是执行腿脚
 */

import { Task, TaskInput, TaskResult } from './task';

/**
 * Worker 类型
 */
export enum WorkerType {
  LINUX = 'linux',
  MAC = 'mac',
  WIN_YINGDAO = 'win_yingdao',
  OPENCLAW = 'openclaw',
}

/**
 * Worker 状态
 */
export enum WorkerStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  BUSY = 'busy',
  DEGRADED = 'degraded',
}

/**
 * 健康状态
 */
export interface HealthStatus {
  healthy: boolean;
  status: WorkerStatus;
  last_heartbeat: Date;
  metrics: {
    cpu_usage_percent: number;
    memory_usage_mb: number;
    active_tasks: number;
    total_tasks_completed: number;
    avg_task_duration_ms: number;
  };
  errors?: string[];
}

/**
 * 任务句柄
 */
export interface TaskHandle {
  task_id: string;
  worker_id: string;
  session_id: string;
  started_at: Date;
}

/**
 * 任务选项
 */
export interface TaskOptions {
  timeout_ms?: number;
  priority?: 'low' | 'medium' | 'high' | 'critical';
  checkpoint_enabled?: boolean;
}

/**
 * Worker 配置
 */
export interface WorkerConfig {
  id: string;
  name: string;
  type: WorkerType;
  capabilities: string[];
  max_concurrent_tasks?: number;
  heartbeat_interval_ms?: number;
  custom_config?: Record<string, any>;
}

/**
 * Worker 接口
 * 所有 Worker 必须实现这个接口
 */
export interface Worker {
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

/**
 * 任务状态 (Worker视角)
 */
export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'approval_required';
  progress: number;                 // 0-100
  started_at: Date;
  updated_at: Date;
  completed_at?: Date;
  error?: TaskErrorDetail;
  result?: any;
  requires_approval: boolean;
  approval_status?: 'pending' | 'approved' | 'rejected';
}

/**
 * 任务错误详情
 */
export interface TaskErrorDetail {
  code: string;
  message: string;
  details?: any;
  retryable: boolean;
  suggested_action: 'retry' | 'manual' | 'skip' | 'escalate';
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
 * 错误分类
 */
export interface ErrorClassification {
  category: 'transient' | 'permanent' | 'business' | 'system';
  code: string;
  retryable: boolean;
  suggested_action: 'retry' | 'retry_with_delay' | 'manual' | 'skip' | 'escalate';
  retry_delay_ms?: number;
  max_retries?: number;
}

/**
 * 重试决策
 */
export interface RetryDecision {
  should_retry: boolean;
  delay_ms: number;
  max_retries: number;
  reason: string;
}

/**
 * Linux Worker 特定配置
 */
export interface LinuxWorkerConfig extends WorkerConfig {
  type: WorkerType.LINUX;
  ssh_host: string;
  ssh_port: number;
  ssh_user: string;
  ssh_key_path?: string;
  working_dir?: string;
}

/**
 * OpenClaw Worker 特定配置
 */
export interface OpenClawWorkerConfig extends WorkerConfig {
  type: WorkerType.OPENCLAW;
  gateway_url: string;
  api_token?: string;
  default_channel?: string;
}

/**
 * 影刀 Worker 特定配置
 */
export interface YingdaoWorkerConfig extends WorkerConfig {
  type: WorkerType.WIN_YINGDAO;
  windows_host: string;
  yingdao_api_url: string;
  yingdao_api_key: string;
  flow_runner_path?: string;
}

/**
 * Worker 注册信息
 */
export interface WorkerRegistration {
  worker_id: string;
  worker_type: WorkerType;
  name: string;
  capabilities: string[];
  registered_at: Date;
  last_heartbeat: Date;
}
