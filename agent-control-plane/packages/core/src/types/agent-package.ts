/**
 * AgentPackage - 专业 Agent 包类型定义
 *
 * 定义: 可复制、可分享、可配置的专业 agent 模板
 * 职责: 做法
 * 一句话: agent package 是做法
 */

import { JSONSchema7 } from 'json-schema';

/**
 * 风险级别
 */
export enum RiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

/**
 * Worker 类型
 */
export type WorkerType = 'linux' | 'mac' | 'win_yingdao' | 'openclaw';

/**
 * 执行后端
 */
export type ExecutionBackend = 'manager_agent' | 'linux_supervisor' | 'win_yingdao' | 'openclaw_runtime';

/**
 * Fallback 策略
 */
export enum FallbackStrategy {
  FAIL_FAST = 'fail_fast',
  RETRY = 'retry',
  MANUAL = 'manual',
  SKIP = 'skip',
}

/**
 * 能力依赖
 */
export interface CapabilityRequirements {
  platform: string[];               // 需要的平台: ["win_yingdao", "excel"]
  tools: string[];                  // 需要的工具: ["flow_runner", "screenshot"]
  min_versions: Record<string, string>;  // 最低版本要求
}

/**
 * Worker 要求
 */
export interface WorkerRequirements {
  min_memory_mb?: number;
  min_cpu_cores?: number;
  required_plugins?: string[];
}

/**
 * 审批规则
 */
export interface ApprovalRules {
  requires_approval_for_write: boolean;
  requires_approval_for_delete: boolean;
  approval_threshold: number;       // 需要几个审批人 (0-10)
  auto_approve_conditions?: {
    max_amount?: number;
    trusted_sources?: string[];
  };
}

/**
 * 权限边界
 */
export interface PermissionBoundaries {
  allowed_domains?: string[];
  forbidden_paths?: string[];
  max_execution_time_sec?: number;
  max_retry_count?: number;
}

/**
 * 治理规则
 */
export interface GovernanceRules {
  risk_level: RiskLevel;
  approval_rules: ApprovalRules;
  permission_boundaries?: PermissionBoundaries;
}

/**
 * 重试策略
 */
export interface RetryPolicy {
  max_retries: number;
  retry_delay_ms: number;
  backoff_multiplier: number;
  retry_on_errors: string[];
}

/**
 * 升级策略
 */
export interface EscalationPolicy {
  escalate_after_retries: boolean;
  escalate_to: 'manual' | 'supervisor';
  escalation_timeout_ms: number;
}

/**
 * 失败处理
 */
export interface FailureHandling {
  fallback_strategy: FallbackStrategy;
  retry_policy?: RetryPolicy;
  escalation_policy?: EscalationPolicy;
}

/**
 * 资源限制
 */
export interface ResourceLimits {
  max_memory_mb: number;
  max_cpu_percent: number;
  max_network_mb: number;
}

/**
 * 执行配置
 */
export interface ExecutionConfig {
  timeout_ms: number;
  heartbeat_interval_ms: number;
  checkpoint_enabled: boolean;
  resource_limits: ResourceLimits;
}

/**
 * 产物格式
 */
export interface ArtifactFormat {
  screenshots: 'png' | 'jpeg';
  logs: 'json' | 'text';
  receipts: 'json' | 'pdf';
}

/**
 * 产物保留策略
 */
export interface RetentionPolicy {
  keep_artifacts_for_hours: number;
  archive_to: string | null;
}

/**
 * 产物配置
 */
export interface ArtifactsConfig {
  required_artifacts: string[];
  artifact_format: ArtifactFormat;
  retention_policy: RetentionPolicy;
}

/**
 * 可观测性配置
 */
export interface ObservabilityConfig {
  log_level: 'debug' | 'info' | 'warn' | 'error';
  metrics_to_collect: string[];
  custom_tags: Record<string, string>;
}

/**
 * 质量指标
 */
export interface QualityMetrics {
  avg_success_rate: number;
  avg_execution_time_ms: number;
  total_executions: number;
  last_updated: Date;
}

/**
 * 文档
 */
export interface Documentation {
  usage_guide?: string;
  examples?: Array<{
    name: string;
    input: any;
    expected_output: any;
  }>;
  troubleshooting?: string;
}

/**
 * 元数据
 */
export interface Metadata {
  author: string;
  license: string;
  tags: string[];
  categories: string[];
  quality_metrics?: QualityMetrics;
  documentation?: Documentation;
}

/**
 * 依赖
 */
export interface Dependencies {
  agent_packages?: string[];
  shared_libraries?: string[];
  data_schemas?: string[];
}

/**
 * 兼容性
 */
export interface Compatibility {
  min_compatible_version: string;
  deprecated_in?: string;
  deprecated_features?: string[];
}

/**
 * AgentPackage
 */
export interface AgentPackage {
  id: string;
  name: string;
  description: string;
  version: string;
  execution_backend: ExecutionBackend;      // 走哪条执行链
  input_schema: JSONSchema7;
  output_schema: JSONSchema7;
  required_capabilities: CapabilityRequirements;  // 接单 worker 必备能力
  supported_worker_types: WorkerType[];          // 哪些 worker 物种可接
  worker_requirements?: WorkerRequirements;
  governance: GovernanceRules;
  failure_handling: FailureHandling;
  execution: ExecutionConfig;
  artifacts?: ArtifactsConfig;
  observability?: ObservabilityConfig;
  dependencies?: Dependencies;
  compatibility: Compatibility;
  metadata: Metadata;
}

/**
 * Agent Package
 */
export interface AgentPackage {
  // 基本信息
  id: string;
  name: string;
  description: string;
  version: string;

  // 输入输出
  input_schema: JSONSchema7;
  output_schema: JSONSchema7;

  // 能力依赖
  required_capabilities: CapabilityRequirements;
  supported_worker_types: WorkerType[];
  worker_requirements?: WorkerRequirements;

  // 治理规则
  governance: GovernanceRules;

  // 失败处理
  failure_handling: FailureHandling;

  // 执行配置
  execution: ExecutionConfig;

  // 产物配置
  artifacts: ArtifactsConfig;

  // 可观测性
  observability: ObservabilityConfig;

  // 依赖和兼容性
  dependencies?: Dependencies;
  compatibility: Compatibility;

  // 元数据
  metadata: Metadata;

  // 时间戳
  created_at: Date;
  updated_at: Date;
}

/**
 * 创建 AgentPackage 参数
 */
export interface CreateAgentPackageParams {
  id: string;
  name: string;
  description: string;
  version: string;
  input_schema: JSONSchema7;
  output_schema: JSONSchema7;
  required_capabilities: CapabilityRequirements;
  supported_worker_types: WorkerType[];
  governance: GovernanceRules;
  failure_handling: FailureHandling;
  execution: ExecutionConfig;
  artifacts: ArtifactsConfig;
  observability: ObservabilityConfig;
  metadata: Metadata;
}

/**
 * 更新 AgentPackage 参数
 */
export interface UpdateAgentPackageParams {
  name?: string;
  description?: string;
  input_schema?: JSONSchema7;
  output_schema?: JSONSchema7;
  governance?: GovernanceRules;
  failure_handling?: FailureHandling;
  metadata?: Partial<Metadata>;
}
