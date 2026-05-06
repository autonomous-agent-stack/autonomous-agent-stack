# Agent Package Manifest 规范 v0

> **创建时间**: 2026-03-31 14:35
> **目标**: 确保 AgentPackage 不是"prompt 包装纸"

---

## 核心原则

**AgentPackage 不是配置文件，是可复制的专业能力单元**

它必须包含:
1. ✅ 输入输出的强类型约束
2. ✅ 能力依赖声明
3. ✅ 风险和治理规则
4. ✅ 失败处理策略
5. ✅ 版本和兼容性

---

## 完整 Manifest Schema

```typescript
interface AgentPackageManifest {
  // ========== 基本信息 ==========
  id: string;                    // 唯一标识: yingdao_form_fill_agent_v0
  name: string;                  // 显示名: "影刀表单录入 Agent"
  description: string;           // 功能描述
  version: string;               // 语义化版本: 0.1.0
  
  // ========== 输入输出 (硬约束) ==========
  input_schema: JSONSchema;      // 输入的强类型定义
  output_schema: JSONSchema;     // 输出的强类型定义
  
  // ========== 能力依赖 ==========
  required_capabilities: {
    platform: string[];          // 需要的平台: ["win_yingdao", "excel"]
    tools: string[];             // 需要的工具: ["flow_runner", "screenshot"]
    min_versions: {              // 最低版本要求
      [platform: string]: string;
    };
  };
  
  // ========== Worker 兼容性 ==========
  supported_worker_types: WorkerType[];  // 支持的 worker 类型
  worker_requirements?: {                // worker 额外要求
    min_memory?: number;                 // 最小内存(MB)
    min_cpu?: number;                    // 最小 CPU 核心数
    required_plugins?: string[];         // 必需的插件
  };
  
  // ========== 治理规则 ==========
  governance: {
    risk_level: 'low' | 'medium' | 'high' | 'critical';
    
    // 审批规则
    approval_rules: {
      requires_approval_for_write: boolean;  // 写操作是否需要审批
      requires_approval_for_delete: boolean; // 删除是否需要审批
      approval_threshold: number;            // 需要几个审批人(0-10)
      auto_approve_conditions?: {            // 自动批准条件
        max_amount?: number;                 // 最大金额
        trusted_sources?: string[];          // 受信来源
      };
    };
    
    // 权限边界
    permission_boundaries: {
      allowed_domains?: string[];            // 允许访问的域名
      forbidden_paths?: string[];            // 禁止访问的路径
      max_execution_time?: number;           // 最大执行时间(秒)
      max_retry_count?: number;              // 最大重试次数
    };
  };
  
  // ========== 失败处理 ==========
  failure_handling: {
    fallback_strategy: 'fail_fast' | 'retry' | 'manual' | 'skip';
    
    retry_policy?: {
      max_retries: number;                   // 最大重试次数
      retry_delay_ms: number;                // 重试延迟
      backoff_multiplier: number;            // 退避乘数
      retry_on_errors: string[];             // 可重试的错误类型
    };
    
    escalation_policy?: {
      escalate_after_retries: boolean;       // 重试失败后是否升级
      escalate_to: 'manual' | 'supervisor';  // 升级目标
      escalation_timeout_ms: number;         // 升级超时
    };
  };
  
  // ========== 执行配置 ==========
  execution: {
    timeout_ms: number;                      // 超时时间
    heartbeat_interval_ms: number;           // 心跳间隔
    checkpoint_enabled: boolean;             // 是否启用检查点
    
    // 资源限制
    resource_limits: {
      max_memory_mb: number;
      max_cpu_percent: number;
      max_network_mb: number;
    };
  };
  
  // ========== 输出与产物业 ==========
  artifacts: {
    required_artifacts: string[];            // 必须产生的产物: ["screenshot", "log", "receipt"]
    artifact_format: {
      screenshots: 'png' | 'jpeg';
      logs: 'json' | 'text';
      receipts: 'json' | 'pdf';
    };
    retention_policy: {
      keep_artifacts_for_hours: number;      // 产物保留时间
      archive_to: string | null;             // 归档位置
    };
  };
  
  // ========== 可观测性 ==========
  observability: {
    log_level: 'debug' | 'info' | 'warn' | 'error';
    metrics_to_collect: string[];            // 要收集的指标
    custom_tags: Record<string, string>;     // 自定义标签
  };
  
  // ========== 依赖与兼容性 ==========
  dependencies: {
    agent_packages?: string[];               // 依赖的其他 agent package
    shared_libraries?: string[];             // 共享库
    data_schemas?: string[];                 // 数据 schema
  };
  
  compatibility: {
    min_compatible_version: string;          // 最低兼容版本
    deprecated_in?: string;                  // 废弃版本
    deprecated_features?: string[];          // 废弃特性
  };
  
  // ========== 元数据 ==========
  metadata: {
    author: string;
    license: string;
    tags: string[];
    categories: string[];
    
    // 质量指标
    quality_metrics?: {
      avg_success_rate: number;              // 平均成功率
      avg_execution_time_ms: number;         // 平均执行时间
      total_executions: number;              // 总执行次数
      last_updated: timestamp;
    };
    
    // 文档
    documentation: {
      usage_guide?: string;                  // 使用指南 URL
      examples?: Array<{                     // 示例
        name: string;
        input: any;
        expected_output: any;
      }>;
      troubleshooting?: string;              // 故障排除指南
    };
  };
}
```

---

## JSON Schema 验证示例

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "id",
    "name",
    "version",
    "input_schema",
    "output_schema",
    "required_capabilities",
    "supported_worker_types",
    "governance",
    "failure_handling",
    "execution"
  ],
  
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*(_v[0-9]+)?$"
    },
    
    "governance": {
      "type": "object",
      "required": ["risk_level", "approval_rules"],
      "properties": {
        "risk_level": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        },
        "approval_rules": {
          "type": "object",
          "required": ["requires_approval_for_write"],
          "properties": {
            "requires_approval_for_write": {"type": "boolean"},
            "approval_threshold": {
              "type": "number",
              "minimum": 0,
              "maximum": 10
            }
          }
        }
      }
    },
    
    "failure_handling": {
      "type": "object",
      "required": ["fallback_strategy"],
      "properties": {
        "fallback_strategy": {
          "type": "string",
          "enum": ["fail_fast", "retry", "manual", "skip"]
        },
        "retry_policy": {
          "type": "object",
          "properties": {
            "max_retries": {"type": "number", "minimum": 0, "maximum": 10},
            "retry_delay_ms": {"type": "number", "minimum": 0},
            "retry_on_errors": {
              "type": "array",
              "items": {"type": "string"}
            }
          }
        }
      }
    }
  }
}
```

---

## 实际示例: 影刀表单录入 Agent

```json
{
  "id": "yingdao_form_fill_agent_v0",
  "name": "影刀表单录入 Agent",
  "description": "自动录入客户订单信息到 ERP 系统",
  "version": "0.1.0",
  
  "input_schema": {
    "type": "object",
    "required": ["customer_name", "order_id", "amount"],
    "properties": {
      "customer_name": {
        "type": "string",
        "minLength": 2,
        "maxLength": 100,
        "description": "客户姓名"
      },
      "order_id": {
        "type": "string",
        "pattern": "^ORD[0-9]{8}$",
        "description": "订单号，格式: ORD + 8位数字"
      },
      "amount": {
        "type": "number",
        "minimum": 0.01,
        "maximum": 999999.99,
        "description": "订单金额"
      },
      "priority": {
        "type": "string",
        "enum": ["normal", "urgent", "critical"],
        "default": "normal"
      }
    }
  },
  
  "output_schema": {
    "type": "object",
    "required": ["success", "receipt"],
    "properties": {
      "success": {"type": "boolean"},
      "receipt": {
        "type": "object",
        "properties": {
          "erp_id": {"type": "string"},
          "timestamp": {"type": "string", "format": "date-time"},
          "operator": {"type": "string"}
        }
      },
      "artifacts": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "type": {"type": "string", "enum": ["screenshot", "log", "file"]},
            "path": {"type": "string"},
            "size": {"type": "number"}
          }
        }
      }
    }
  },
  
  "required_capabilities": {
    "platform": ["win_yingdao"],
    "tools": ["flow_runner", "screenshot", "file_system"],
    "min_versions": {
      "win_yingdao": "3.0.0"
    }
  },
  
  "supported_worker_types": ["win_yingdao"],
  
  "governance": {
    "risk_level": "high",
    "approval_rules": {
      "requires_approval_for_write": true,
      "requires_approval_for_delete": true,
      "approval_threshold": 1,
      "auto_approve_conditions": {
        "max_amount": 1000,
        "trusted_sources": ["internal_system", "verified_api"]
      }
    },
    "permission_boundaries": {
      "max_execution_time": 300,
      "max_retry_count": 3
    }
  },
  
  "failure_handling": {
    "fallback_strategy": "manual",
    "retry_policy": {
      "max_retries": 2,
      "retry_delay_ms": 5000,
      "backoff_multiplier": 2,
      "retry_on_errors": ["NETWORK_ERROR", "TIMEOUT", "ERP_BUSY"]
    },
    "escalation_policy": {
      "escalate_after_retries": true,
      "escalate_to": "manual",
      "escalation_timeout_ms": 60000
    }
  },
  
  "execution": {
    "timeout_ms": 300000,
    "heartbeat_interval_ms": 10000,
    "checkpoint_enabled": true,
    "resource_limits": {
      "max_memory_mb": 512,
      "max_cpu_percent": 80,
      "max_network_mb": 100
    }
  },
  
  "artifacts": {
    "required_artifacts": ["screenshot", "log", "receipt"],
    "artifact_format": {
      "screenshots": "png",
      "logs": "json",
      "receipts": "json"
    },
    "retention_policy": {
      "keep_artifacts_for_hours": 168,
      "archive_to": "s3://agent-artifacts"
    }
  },
  
  "observability": {
    "log_level": "info",
    "metrics_to_collect": [
      "execution_time",
      "success_rate",
      "retry_count",
      "approval_rate"
    ],
    "custom_tags": {
      "domain": "erp",
      "team": "finance"
    }
  },
  
  "dependencies": {},
  "compatibility": {
    "min_compatible_version": "0.1.0"
  },
  
  "metadata": {
    "author": "Your Name",
    "license": "MIT",
    "tags": ["erp", "form", "automation", "yingdao"],
    "categories": ["data-entry", "finance"],
    "quality_metrics": {
      "avg_success_rate": 0.95,
      "avg_execution_time_ms": 15000,
      "total_executions": 0,
      "last_updated": "2026-03-31T14:35:00Z"
    },
    "documentation": {
      "usage_guide": "https://docs.example.com/yingdao-form-fill",
      "examples": [
        {
          "name": "标准订单录入",
          "input": {
            "customer_name": "张三",
            "order_id": "ORD20260331",
            "amount": 1500.00
          },
          "expected_output": {
            "success": true,
            "receipt": {
              "erp_id": "ERP123456"
            }
          }
        }
      ]
    }
  }
}
```

---

## 验证器实现(Typescript)

```typescript
import Ajv from 'ajv';

export class AgentPackageValidator {
  private ajv: Ajv;
  
  constructor() {
    this.ajv = new Ajv({
      allErrors: true,
      verbose: true,
      strict: true
    });
    
    // 加载 manifest schema
    this.loadManifestSchema();
  }
  
  /**
   * 验证 manifest 是否符合规范
   */
  validate(manifest: any): ValidationResult {
    const validate = this.ajv.getSchema('AgentPackageManifest');
    if (!validate) {
      throw new Error('Schema not loaded');
    }
    
    const valid = validate(manifest);
    
    if (!valid) {
      return {
        valid: false,
        errors: validate.errors?.map(err => ({
          path: err.instancePath,
          message: err.message || '',
          params: err.params
        })) || []
      };
    }
    
    // 额外的业务规则验证
    const businessErrors = this.validateBusinessRules(manifest);
    if (businessErrors.length > 0) {
      return {
        valid: false,
        errors: businessErrors
      };
    }
    
    return { valid: true };
  }
  
  /**
   * 业务规则验证
   */
  private validateBusinessRules(manifest: AgentPackageManifest): ValidationError[] {
    const errors: ValidationError[] = [];
    
    // 规则1: 高风险必须有审批
    if (manifest.governance.risk_level === 'high' || 
        manifest.governance.risk_level === 'critical') {
      if (!manifest.governance.approval_rules.requires_approval_for_write) {
        errors.push({
          path: 'governance.approval_rules',
          message: 'High/critical risk packages must require approval for write operations'
        });
      }
    }
    
    // 规则2: 重试策略必须与 fallback 匹配
    if (manifest.failure_handling.fallback_strategy === 'retry') {
      if (!manifest.failure_handling.retry_policy) {
        errors.push({
          path: 'failure_handling',
          message: 'Retry strategy requires retry_policy to be defined'
        });
      }
    }
    
    // 规则3: 必须至少支持一种 worker
    if (manifest.supported_worker_types.length === 0) {
      errors.push({
        path: 'supported_worker_types',
        message: 'At least one worker type must be supported'
      });
    }
    
    // 规则4: 输入 schema 不能为空
    if (!manifest.input_schema.properties || 
        Object.keys(manifest.input_schema.properties).length === 0) {
      errors.push({
        path: 'input_schema',
        message: 'Input schema must define at least one property'
      });
    }
    
    return errors;
  }
  
  private loadManifestSchema(): void {
    // 加载上面定义的 JSON Schema
    const schema = { /* JSON Schema 定义 */ };
    this.ajv.addSchema(schema, 'AgentPackageManifest');
  }
}

interface ValidationResult {
  valid: boolean;
  errors?: ValidationError[];
}

interface ValidationError {
  path: string;
  message: string;
  params?: any;
}
```

---

## 导出/导入工具

```typescript
/**
 * Agent Package 导出器
 */
export class AgentPackageExporter {
  /**
   * 导出 package 为可分享的格式
   */
  async exportPackage(
    packageId: string,
    options: {
      includeArtifacts?: boolean;  // 是否包含示例产物
      includeTests?: boolean;      // 是否包含测试用例
      format: 'json' | 'yaml' | 'zip';
    }
  ): Promise<Buffer> {
    const manifest = await this.loadManifest(packageId);
    const validator = new AgentPackageValidator();
    const validation = validator.validate(manifest);
    
    if (!validation.valid) {
      throw new Error(`Invalid manifest: ${JSON.stringify(validation.errors)}`);
    }
    
    switch (options.format) {
      case 'json':
        return Buffer.from(JSON.stringify(manifest, null, 2));
      
      case 'yaml':
        const yaml = require('yaml');
        return Buffer.from(yaml.stringify(manifest));
      
      case 'zip':
        return await this.createZipPackage(manifest, options);
    }
  }
  
  /**
   * 导入 package
   */
  async importPackage(
    data: Buffer,
    options: {
      validateOnly?: boolean;
      overwrite?: boolean;
    }
  ): Promise<AgentPackageManifest> {
    // 解析
    const manifest = JSON.parse(data.toString());
    
    // 验证
    const validator = new AgentPackageValidator();
    const validation = validator.validate(manifest);
    
    if (!validation.valid) {
      throw new Error(`Invalid manifest: ${JSON.stringify(validation.errors)}`);
    }
    
    // 检查兼容性
    await this.checkCompatibility(manifest);
    
    // 保存
    if (!options.validateOnly) {
      await this.saveManifest(manifest, options.overwrite);
    }
    
    return manifest;
  }
}
```

---

## 自查结果

### ✅ 1. AgentPackage manifest 字段够硬吗？

**答**: 是的。

**硬约束字段**:
- ✅ 输入/输出 schema (强类型 JSON Schema)
- ✅ 能力依赖 (platform/tools/min_versions)
- ✅ Worker 兼容性 (supported_worker_types + requirements)
- ✅ 风险级别 (risk_level + approval_rules + permission_boundaries)
- ✅ 审批规则 (threshold + auto_approve_conditions)
- ✅ Fallback 策略 (retry_policy + escalation_policy)
- ✅ 版本号 (语义化版本 + min_compatible_version)
- ✅ 依赖声明 (agent_packages + shared_libraries)

**不是 prompt 包装纸的证据**:
1. 强类型输入输出，无法随便传
2. 治理规则明确，高风险必须审批
3. 失败处理策略清晰，不是"让AI自己看着办"
4. 可观测性内置，强制收集指标
5. 质量指标可追踪，运行时更新

---

**下一步**: 自查 Win+影刀 Worker Contract
