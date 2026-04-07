/**
 * WinYingdaoWorker - 影刀 Worker Contract
 *
 * 定义影刀 Worker 的接口契约
 */

import { Task } from '@agent-control-plane/core';

/**
 * 影刀任务选项
 */
export interface YingdaoTaskOptions {
  flow_id: string;
  flow_version?: string;
  inputs: Record<string, any>;
  timeout_ms?: number;
  screenshot_interval_ms?: number;
  save_logs?: boolean;
}

/**
 * 影刀任务句柄
 */
export interface YingdaoTaskHandle {
  task_id: string;
  worker_id: string;
  flow_run_id: string;
  windows_session_id: string;
  started_at: Date;
}

/**
 * 影刀运行状态
 */
export interface YingdaoRunStatus {
  task_id: string;
  flow_run_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  progress: {
    current_step: number;
    total_steps: number;
    current_step_name: string;
    percent: number;
  };
  started_at: Date;
  updated_at: Date;
  completed_at?: Date;
  error?: YingdaoError;
  checkpoints?: Checkpoint[];
}

/**
 * 影刀错误
 */
export interface YingdaoError {
  code: string;
  message: string;
  step_name?: string;
  screenshot_path?: string;
  log_path?: string;
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
      crash_time: Date;
    };
  };
  retryable: boolean;
  suggested_action: 'retry' | 'retry_with_delay' | 'manual' | 'skip' | 'escalate';
}

/**
 * 影刀产物
 */
export interface YingdaoArtifact {
  type: 'screenshot' | 'log' | 'receipt' | 'excel' | 'pdf' | 'metadata';
  path: string;
  size_bytes: number;
  mime_type: string;
  created_at: Date;
  metadata: Record<string, any>;
  flow_run_id: string;
  step_name?: string;
  screenshot_info?: {
    element_selector?: string;
    before_action?: boolean;
    after_action?: boolean;
    on_error?: boolean;
  };
  receipt_info?: {
    system: string;
    record_id: string;
    timestamp: Date;
    operator: string;
  };
}

/**
 * 检查点
 */
export interface Checkpoint {
  name: string;
  timestamp: Date;
  state: Record<string, any>;
  artifacts: YingdaoArtifact[];
}

/**
 * 错误分类
 */
export interface YingdaoErrorClassification {
  category: 'transient' | 'permanent' | 'business' | 'system';
  code: string;
  retryable: boolean;
  suggested_action: 'retry' | 'retry_with_delay' | 'manual' | 'skip' | 'escalate';
  retry_delay_ms?: number;
  max_retries?: number;
}

/**
 * WinYingdaoWorkerContract 接口
 *
 * 所有影刀 Worker 必须实现这个接口
 */
export interface WinYingdaoWorkerContract {
  /**
   * 启动任务
   */
  startTask(task: Task, options: YingdaoTaskOptions): Promise<YingdaoTaskHandle>;

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
  cancelRun(handle: YingdaoTaskHandle, reason?: string): Promise<void>;

  /**
   * 分类错误 (同步)
   */
  classifyError(error: Error): YingdaoErrorClassification;
}
