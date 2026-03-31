# Agent Package Runtime Minimal Schema

> **Day 5-6: 运行时最小集**
> **目标**: 可验证、可复制、可分享的运行单元

---

## 核心原则

**只保留 runtime 真会消费的字段**

---

## Runtime Minimal Schema

```typescript
/**
 * Agent Package 运行时最小集
 * 
 * 删除/简化:
 * - ❌ 删除: quality_metrics, documentation, compatibility
 * - ❌ 简化: governance (只保留 risk + approval + timeout)
 * - ❌ 简化: failure_handling (只保留 fallback + retries)
 * - ❌ 简化: execution (只保留 timeout + heartbeat)
 * - ❌ 简化: artifacts (只保留 required_artifacts)
 */
export interface AgentPackageRuntimeMinimal {
  // ========== 基本信息 ==========
  id: string;
  version: string;
  
  // ========== 输入输出 (强约束) ==========
  input_schema: JSONSchema7;
  output_schema: JSONSchema7;
  
  // ========== 能力依赖 ==========
  required_capabilities: {
    platform: string[];
    tools: string[];
    min_versions: Record<string, string>;
  };
  
  // ========== Worker 兼容性 ==========
  supported_worker_types: WorkerType[];
  
  // ========== 治理规则 (简化版) ==========
  governance: {
    risk_level: 'low' | 'medium' | 'high' | 'critical';
    requires_approval_for_write: boolean;
    max_execution_time_sec: number;
  };
  
  // ========== 失败处理 (简化版) ==========
  failure_handling: {
    fallback_strategy: 'fail_fast' | 'retry' | 'manual';
    max_retries: number;
  };
  
  // ========== 执行配置 (简化版) ==========
  execution: {
    timeout_ms: number;
    heartbeat_interval_ms: number;
  };
  
  // ========== 产物 (最小集) ==========
  artifacts: {
    required_artifacts: string[];  // ["log", "screenshot", "receipt"]
  };
}
```

---

## JSON Schema 验证

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "id",
    "version",
    "input_schema",
    "output_schema",
    "required_capabilities",
    "supported_worker_types",
    "governance",
    "failure_handling",
    "execution",
    "artifacts"
  ],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*(_v[0-9]+)?$"
    },
    "version": {
      "type": "string",
      "pattern": "^0\\.[1-9][0-9]*\\.[0-9]+$"
    },
    "input_schema": {
      "type": "object",
      "required": ["type", "properties"],
      "properties": {
        "type": {"type": "string"},
        "properties": {"type": "object"}
      }
    },
    "output_schema": {
      "type": "object",
      "required": ["type", "properties"],
      "properties": {
        "type": {"type": "string"},
        "properties": {"type": "object"}
      }
    },
    "required_capabilities": {
      "type": "object",
      "required": ["platform", "tools"],
      "properties": {
        "platform": {
          "type": "array",
          "items": {"type": "string"}
        },
        "tools": {
          "type": "array",
          "items": {"type": "string"}
        },
        "min_versions": {
          "type": "object",
          "additionalProperties": {"type": "string"}
        }
      }
    },
    "supported_worker_types": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "enum": ["linux", "mac", "win_yingdao", "openclaw"]
      }
    },
    "governance": {
      "type": "object",
      "required": ["risk_level", "requires_approval_for_write", "max_execution_time_sec"],
      "properties": {
        "risk_level": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        },
        "requires_approval_for_write": {
          "type": "boolean"
        },
        "max_execution_time_sec": {
          "type": "number",
          "minimum": 1,
          "maximum": 3600
        }
      }
    },
    "failure_handling": {
      "type": "object",
      "required": ["fallback_strategy", "max_retries"],
      "properties": {
        "fallback_strategy": {
          "type": "string",
          "enum": ["fail_fast", "retry", "manual"]
        },
        "max_retries": {
          "type": "number",
          "minimum": 0,
          "maximum": 10
        }
      }
    },
    "execution": {
      "type": "object",
      "required": ["timeout_ms", "heartbeat_interval_ms"],
      "properties": {
        "timeout_ms": {
          "type": "number",
          "minimum": 1000,
          "maximum": 3600000
        },
        "heartbeat_interval_ms": {
          "type": "number",
          "minimum": 1000,
          "maximum": 60000
        }
      }
    },
    "artifacts": {
      "type": "object",
      "required": ["required_artifacts"],
      "properties": {
        "required_artifacts": {
          "type": "array",
          "minItems": 1,
          "items": {"type": "string"}
        }
      }
    }
  }
}
```

---

## 不做的事 (Day 5-6)

- ❌ OpenClaw 前台入口
- ❌ Telegram 群聊
- ❌ 长期记忆
- ❌ 真影刀 API 深接
- ❌ UI 漂亮页面
- ❌ 太重的 Prisma/数据库设计

---

## 下一步

实现 Package Validator
