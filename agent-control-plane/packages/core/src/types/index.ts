/**
 * 核心类型定义
 *
 * 导出所有核心类型
 */

export * from './task';
export * from './agent-package';
export * from './worker';

/**
 * 核心抽象 - 三句话
 *
 * 1. Task 是派单
 * 2. AgentPackage 是做法
 * 3. Worker 是执行腿脚
 */

/**
 * 依赖关系
 *
 * Task
 *   ├── 依赖: AgentPackage (验证输入/获取执行规则)
 *   └── 依赖: Worker (执行任务)
 *
 * AgentPackage
 *   ├── 依赖: Worker (声明需要什么类型的 worker)
 *   └── 不依赖: Task (可以被多个任务复用)
 *
 * Worker
 *   ├── 依赖: AgentPackage (知道要执行什么)
 *   └── 不依赖: Task (可以被多个任务复用)
 */

/**
 * 职责边界
 *
 * Task 负责:
 *   - 任务输入
 *   - 任务状态
 *   - 任务结果
 *   - 审批状态
 *   - 错误信息
 *
 * AgentPackage 负责:
 *   - 输入/输出 schema
 *   - 能力依赖
 *   - 治理规则 (风险/审批/权限)
 *   - 失败处理策略
 *   - 版本和兼容性
 *
 * Worker 负责:
 *   - 执行任务
 *   - 报告状态
 *   - 返回产物
 *   - 分类错误
 *   - 健康检查
 */
