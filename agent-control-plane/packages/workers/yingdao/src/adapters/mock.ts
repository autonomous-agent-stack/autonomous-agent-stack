/**
 * MockYingdaoWorkerAdapter - 假实现可跑
 *
 * 用于开发和测试，不依赖真实影刀环境
 */

import { Task } from '@agent-control-plane/core';
import {
  WinYingdaoWorkerContract,
  YingdaoTaskOptions,
  YingdaoTaskHandle,
  YingdaoRunStatus,
  YingdaoArtifact,
  YingdaoErrorClassification
} from '../contract';

/**
 * Mock 影刀 Worker Adapter
 */
export class MockYingdaoWorkerAdapter implements WinYingdaoWorkerContract {
  private runs: Map<string, MockRun> = new Map();
  private currentStep = 0;

  /**
   * 启动任务
   */
  async startTask(task: Task, options: YingdaoTaskOptions): Promise<YingdaoTaskHandle> {
    const flowRunId = `mock-run-${Date.now()}`;
    
    // 创建模拟运行
    const mockRun: MockRun = {
      task_id: task.id,
      flow_run_id: flowRunId,
      flow_id: options.flow_id,
      inputs: options.inputs,
      status: 'running',
      started_at: new Date(),
      updated_at: new Date(),
      progress: {
        current_step: 0,
        total_steps: 5,
        current_step_name: '准备启动',
        percent: 0
      }
    };
    
    this.runs.set(flowRunId, mockRun);
    
    // 模拟进度更新
    this.simulateProgress(flowRunId);
    
    return {
      task_id: task.id,
      worker_id: 'mock-worker',
      flow_run_id: flowRunId,
      windows_session_id: 'mock-session',
      started_at: new Date()
    };
  }

  /**
   * 查询运行状态
   */
  async getRunStatus(handle: YingdaoTaskHandle): Promise<YingdaoRunStatus> {
    const run = this.runs.get(handle.flow_run_id);
    
    if (!run) {
      throw new Error(`Run not found: ${handle.flow_run_id}`);
    }
    
    return {
      task_id: run.task_id,
      flow_run_id: run.flow_run_id,
      status: run.status,
      progress: run.progress,
      started_at: run.started_at,
      updated_at: run.updated_at,
      completed_at: run.completed_at
    };
  }

  /**
   * 拉取产物
   */
  async getArtifacts(handle: YingdaoTaskHandle): Promise<YingdaoArtifact[]> {
    const run = this.runs.get(handle.flow_run_id);
    
    if (!run) {
      throw new Error(`Run not found: ${handle.flow_run_id}`);
    }
    
    // 只在完成后返回产物
    if (run.status !== 'completed') {
      return [];
    }
    
    return [
      {
        type: 'log',
        path: '/artifacts/mock-run.log',
        size_bytes: 1024,
        mime_type: 'application/json',
        created_at: new Date(),
        metadata: {},
        flow_run_id: run.flow_run_id
      },
      {
        type: 'screenshot',
        path: '/artifacts/mock-final.png',
        size_bytes: 204800,
        mime_type: 'image/png',
        created_at: new Date(),
        metadata: {},
        flow_run_id: run.flow_run_id,
        screenshot_info: {
          after_action: true
        }
      },
      {
        type: 'receipt',
        path: '/artifacts/mock-receipt.json',
        size_bytes: 512,
        mime_type: 'application/json',
        created_at: new Date(),
        metadata: {},
        flow_run_id: run.flow_run_id,
        receipt_info: {
          system: 'MOCK_ERP',
          record_id: 'MOCK-123',
          timestamp: new Date(),
          operator: 'mock-worker'
        }
      }
    ];
  }

  /**
   * 取消运行
   */
  async cancelRun(handle: YingdaoTaskHandle, reason?: string): Promise<void> {
    const run = this.runs.get(handle.flow_run_id);
    
    if (run) {
      run.status = 'cancelled';
      run.updated_at = new Date();
      run.completed_at = new Date();
      console.log(`[Mock] Cancelled ${handle.flow_run_id}: ${reason}`);
    }
  }

  /**
   * 分类错误
   */
  async classifyError(error: Error): Promise<YingdaoErrorClassification> {
    const message = error.message.toUpperCase();
    
    // 瞬时错误
    if (message.includes('TIMEOUT') || message.includes('NETWORK') || message.includes('BUSY')) {
      return {
        category: 'transient',
        code: message.includes('TIMEOUT') ? 'TIMEOUT' : 'NETWORK_ERROR',
        retryable: true,
        suggested_action: 'retry_with_delay',
        retry_delay_ms: 5000,
        max_retries: 3
      };
    }
    
    // 永久错误
    if (message.includes('NOT_FOUND') || message.includes('AUTH_FAILED') || message.includes('CRASHED')) {
      return {
        category: 'permanent',
        code: message.includes('NOT_FOUND') ? 'ELEMENT_NOT_FOUND' : 'AUTH_FAILED',
        retryable: false,
        suggested_action: 'manual'
      };
    }
    
    // 业务错误
    if (message.includes('DUPLICATE') || message.includes('VALIDATION')) {
      return {
        category: 'business',
        code: message.includes('DUPLICATE') ? 'DUPLICATE_RECORD' : 'VALIDATION_FAILED',
        retryable: false,
        suggested_action: message.includes('DUPLICATE') ? 'skip' : 'manual'
      };
    }
    
    // 默认为系统错误
    return {
      category: 'system',
      code: 'UNKNOWN_ERROR',
      retryable: false,
      suggested_action: 'escalate'
    };
  }

  /**
   * 模拟进度更新
   */
  private simulateProgress(flowRunId: string): void {
    const steps = [
      { name: '打开 ERP', percent: 20 },
      { name: '导航到页面', percent: 40 },
      { name: '填写表单', percent: 60 },
      { name: '提交订单', percent: 80 },
      { name: '完成', percent: 100 }
    ];
    
    let stepIndex = 0;
    
    const interval = setInterval(() => {
      const run = this.runs.get(flowRunId);
      
      if (!run || run.status === 'cancelled') {
        clearInterval(interval);
        return;
      }
      
      if (stepIndex >= steps.length) {
        run.status = 'completed';
        run.completed_at = new Date();
        run.updated_at = new Date();
        clearInterval(interval);
        return;
      }
      
      const step = steps[stepIndex];
      run.progress = {
        current_step: stepIndex + 1,
        total_steps: steps.length,
        current_step_name: step.name,
        percent: step.percent
      };
      run.updated_at = new Date();
      
      stepIndex++;
    }, 1000); // 每秒更新一次
  }
}

/**
 * 模拟运行
 */
interface MockRun {
  task_id: string;
  flow_run_id: string;
  flow_id: string;
  inputs: Record<string, any>;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: Date;
  updated_at: Date;
  completed_at?: Date;
  progress: {
    current_step: number;
    total_steps: number;
    current_step_name: string;
    percent: number;
  };
}
