# Day 5-6: Agent Package 规范 (运行时最小集)

> **分支**: feature/agent-control-plane-v0-sprint18
> **时间**: 2026-03-31 15:50
> **目标**: 可验证、可复制、可分享的运行单元

---

## 核心原则

**不是"把规范写全"，而是"把规范做成能校验、能复用、能拒绝坏包的最小运行标准"**

---

## Day 5-6 只做 4 件事

### 1. 收缩成运行时最小集

**只定义真正会被系统消费的字段**:

```
✅ Runtime Required:
- id
- version
- input_schema
- output_schema
- required_capabilities
- supported_worker_types
- governance (risk_level, approval_rules, permission_boundaries)
- failure_handling (fallback_strategy, retry_policy)
- execution (timeout_ms, heartbeat_interval_ms, resource_limits)
- artifacts (required_artifacts, artifact_format)

❌ Metadata Optional (Day 5-6 不依赖):
- quality_metrics
- 大段 metadata
- 外部文档链接 (usage_guide, examples, troubleshooting)
- compatibility (废弃字段)
- observability.custom_tags
```

**区分**: Runtime Required vs Metadata Optional

---

### 2. 做 Package Validator

**最值钱的产物**: 不是 spec 文档，而是 **能校验的代码**

**交付**:
- [ ] Schema 校验器 (TypeScript/AJV)
- [ ] 示例 package 能过校验
- [ ] 坏 package 会被明确拒绝

**验收**:
```bash
# 好的 package
npm run validate-package packages/agent-packages/form-fill/manifest.json
# ✅ Valid

# 坏的 package (缺少必需字段)
npm run validate-package packages/agent-packages/bad/manifest.json
# ❌ Error: Missing required field: input_schema
```

---

### 3. 做第二个 Package，证明可复制

**只允许少量差异**:
- ✅ flow_id (不同)
- ✅ input/output schema (不同)
- ✅ 审批阈值 (不同)
- ✅ 错误偏好 (不同)
- ✅ artifact 要求 (不同)
- ❌ Contract 不变
- ❌ 80% 以上字段相同

**第二个 Package**: 报表下载并归档 Agent

**复用率**:
- Contract: 100% 相同
- 字段: 80% 相同
- 差异: 只改配置和少量逻辑

---

### 4. 不碰这些

**Day 5-6 不该做的事**:
- ❌ OpenClaw 前台
- ❌ 长期记忆
- ❌ 群聊协作
- ❌ 完整平台特性

**只回答一个问题**:
> Agent Package 到底是不是一个可验证、可复制、可分享的运行单元？

---

## 运行时最小集 Schema

```typescript
interface AgentPackageRuntimeMinimal {
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

**删除/简化**:
- ❌ 删除: quality_metrics, documentation, compatibility
- ❌ 简化: governance (只保留 risk_level + approval + timeout)
- ❌ 简化: failure_handling (只保留 fallback + max_retries)
- ❌ 简化: execution (只保留 timeout + heartbeat)
- ❌ 简化: artifacts (只保留 required_artifacts)

---

## Package Validator

```typescript
// packages/core/src/validation/package-validator.ts
import Ajv from 'ajv';

export class AgentPackageValidator {
  private ajv: Ajv;
  
  constructor() {
    this.ajv = new Ajv({
      allErrors: true,
      strict: true,
      coerceTypes: true
    });
    
    this.loadRuntimeMinimalSchema();
  }
  
  validate(manifest: any): ValidationResult {
    // 1. Schema 验证
    const schemaValid = this.ajv.validate('AgentPackageRuntimeMinimal', manifest);
    if (!schemaValid) {
      return {
        valid: false,
        errors: this.ajv.errors?.map(err => ({
          field: err.instancePath,
          message: err.message || ''
        })) || []
      };
    }
    
    // 2. 业务规则验证
    const businessErrors = this.validateBusinessRules(manifest);
    if (businessErrors.length > 0) {
      return {
        valid: false,
        errors: businessErrors
      };
    }
    
    return { valid: true };
  }
  
  private validateBusinessRules(pkg: AgentPackageRuntimeMinimal): ValidationError[] {
    const errors: ValidationError[] = [];
    
    // 规则1: 高风险必须有审批
    if (pkg.governance.risk_level === 'high' && !pkg.governance.requires_approval_for_write) {
      errors.push({
        field: 'governance.requires_approval_for_write',
        message: 'High risk packages must require approval for write operations'
      });
    }
    
    // 规则2: 必须支持至少一种 worker
    if (pkg.supported_worker_types.length === 0) {
      errors.push({
        field: 'supported_worker_types',
        message: 'At least one worker type must be supported'
      });
    }
    
    // 规则3: input_schema 不能为空
    if (!pkg.input_schema.properties || Object.keys(pkg.input_schema.properties).length === 0) {
      errors.push({
        field: 'input_schema',
        message: 'Input schema must define at least one property'
      });
    }
    
    // 规则4: 必须包含 log 产物
    if (!pkg.artifacts.required_artifacts.includes('log')) {
      errors.push({
        field: 'artifacts.required_artifacts',
        message: 'Must include "log" artifact'
      });
    }
    
    return errors;
  }
  
  private loadRuntimeMinimalSchema(): void {
    const schema = {
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
        "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*(_v[0-9]+)?$"},
        "version": {"type": "string", "pattern": "^0\\.[1-9][0-9]*\\.[0-9]+$"},
        // ... 其他字段
      }
    };
    
    this.ajv.addSchema(schema, 'AgentPackageRuntimeMinimal');
  }
}

interface ValidationResult {
  valid: boolean;
  errors?: ValidationError[];
}

interface ValidationError {
  field: string;
  message: string;
}
```

---

## 第二个 Package: 报表下载并归档 Agent

### 只改这些

**差异点** (20%):
```diff
{
-  "id": "yingdao_form_fill_agent_v0",
+  "id": "yingdao_report_download_agent_v0",
   
-  "name": "影刀表单录入 Agent",
+  "name": "报表下载并归档 Agent",
   
   "input_schema": {
-    "properties": {
-      "customer_name": {"type": "string"},
-      "order_id": {"type": "string"},
-      "amount": {"type": "number"}
-    }
+    "properties": {
+      "report_date": {"type": "string", "format": "date"},
+      "report_type": {"type": "string"},
+      "archive_path": {"type": "string"}
+    }
   },
   
   "governance": {
-    "risk_level": "high",
-    "requires_approval_for_write": true
+    "risk_level": "medium",
+    "requires_approval_for_write": false
   }
}
```

**保持相同** (80%):
- Contract 结构
- required_capabilities
- supported_worker_types
- failure_handling
- execution
- artifacts
- 其他治理规则

**复用率**: 80% 字段相同，只改配置

---

## 验收标准

### Day 5 完成标志
- [ ] Runtime Minimal Schema 定义
- [ ] Package Validator 实现
- [ ] 示例 form-fill package 能过校验
- [ ] 坏 package 会被明确拒绝

### Day 6 完成标志
- [ ] 第二个 package (report-download) 创建
- [ ] 能过校验
- [ ] 复用率 ≥ 80%
- [ ] Validator 测试覆盖

### 最终验收
**问题**: Agent Package 到底是不是一个可验证、可复制、可分享的运行单元？

**证明**:
1. ✅ 可验证: Validator 能拒绝坏包
2. ✅ 可复制: 第二个 package 只改 20%
3. ✅ 可分享: 包含所有运行时必需信息

---

## 不做的事

- ❌ 不碰 OpenClaw 前台
- ❌ 不碰长期记忆
- ❌ 不碰群聊协作
- ❌ 不做完整平台特性
- ❌ 不写太多文档

---

## 下一步

准备好开始 Day 5-6 了吗？

目标: **运行时最小集 + 可验证规范**
