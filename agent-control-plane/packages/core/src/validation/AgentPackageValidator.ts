/**
 * Agent Package Validator
 *
 * 可验证、可复制、可分享
 */

import Ajv from 'ajv';
import { AgentPackageRuntimeMinimal } from '../schemas/AgentPackageRuntimeMinimal';

export interface ValidationResult {
  valid: boolean;
  errors?: ValidationError[];
}

export interface ValidationError {
  field: string;
  message: string;
}

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

  /**
   * 验证 manifest
   */
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

  /**
   * 业务规则验证
   */
  private validateBusinessRules(pkg: any): ValidationError[] {
    const errors: ValidationError[] = [];

    // 规则1: 高风险必须有审批
    if (pkg.governance?.risk_level === 'high' && !pkg.governance?.requires_approval_for_write) {
      errors.push({
        field: 'governance.requires_approval_for_write',
        message: 'High risk packages must require approval for write operations'
      });
    }

    // 规则2: 必须支持至少一种 worker
    if (!pkg.supported_worker_types || pkg.supported_worker_types.length === 0) {
      errors.push({
        field: 'supported_worker_types',
        message: 'At least one worker type must be supported'
      });
    }

    // 规则3: input_schema 不能为空
    if (!pkg.input_schema?.properties || Object.keys(pkg.input_schema.properties).length === 0) {
      errors.push({
        field: 'input_schema',
        message: 'Input schema must define at least one property'
      });
    }

    // 规则4: 必须包含 log 产物
    if (!pkg.artifacts?.required_artifacts || !pkg.artifacts.required_artifacts.includes('log')) {
      errors.push({
        field: 'artifacts.required_artifacts',
        message: 'Must include "log" artifact'
      });
    }

    // 规则5: 超时时间必须合理
    if (pkg.execution?.timeout_ms && (pkg.execution.timeout_ms < 1000 || pkg.execution.timeout_ms > 3600000)) {
      errors.push({
        field: 'execution.timeout_ms',
        message: 'Timeout must be between 1000 and 3600000 ms'
      });
    }

    // 规则6: 重试次数不能超过 10
    if (pkg.failure_handling?.max_retries !== undefined && (pkg.failure_handling.max_retries < 0 || pkg.failure_handling.max_retries > 10)) {
      errors.push({
        field: 'failure_handling.max_retries',
        message: 'Max retries must be between 0 and 10'
      });
    }

    return errors;
  }

  /**
   * 加载 Schema
   */
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
    };

    this.ajv.addSchema(schema, 'AgentPackageRuntimeMinimal');
  }
}

// 导出单例
export const validator = new AgentPackageValidator();
