/**
 * Agent Package Validator 测试
 *
 * 验证: 合法package能过，坏package会被拒绝
 */

import { AgentPackageValidator } from '../src/validation/AgentPackageValidator';

describe('AgentPackageValidator', () => {
  let validator: AgentPackageValidator;

  beforeAll(() => {
    validator = new AgentPackageValidator();
  });

  describe('✅ 合法的 package 能过校验', () => {
    test('form-fill package (最小运行时集)', () => {
      const formFill = {
        id: 'yingdao_form_fill_agent_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {
            customer_name: {type: 'string'},
            order_id: {type: 'string'},
            amount: {type: 'number'}
          }
        },
        
        output_schema: {
          type: 'object',
          properties: {
            success: {type: 'boolean'},
            receipt: {type: 'object'}
          }
        },
        
        required_capabilities: {
          platform: ['win_yingdao'],
          tools: ['flow_runner', 'screenshot'],
          min_versions: { win_yingdao: '3.0.0' }
        },
        
        supported_worker_types: ['win_yingdao'],
        
        governance: {
          risk_level: 'high',
          requires_approval_for_write: true,
          max_execution_time_sec: 300
        },
        
        failure_handling: {
          fallback_strategy: 'manual',
          max_retries: 2
        },
        
        execution: {
          timeout_ms: 300000,
          heartbeat_interval_ms: 10000
        },
        
        artifacts: {
          required_artifacts: ['log', 'screenshot', 'receipt']
        }
      };

      const result = validator.validate(formFill);
      expect(result.valid).toBe(true);
      expect(result.errors).toBeUndefined();
    });

    test('低风险、不需要审批的 package', () => {
      const lowRisk = {
        id: 'simple_task_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {
            task_name: {type: 'string'}
          }
        },
        
        output_schema: {
          type: 'object',
          properties: {
            done: {type: 'boolean'}
          }
        },
        
        required_capabilities: {
          platform: ['linux'],
          tools: ['shell'],
          min_versions: {}
        },
        
        supported_worker_types: ['linux'],
        
        governance: {
          risk_level: 'low',
          requires_approval_for_write: false,
          max_execution_time_sec: 60
        },
        
        failure_handling: {
          fallback_strategy: 'fail_fast',
          max_retries: 0
        },
        
        execution: {
          timeout_ms: 60000,
          heartbeat_interval_ms: 5000
        },
        
        artifacts: {
          required_artifacts: ['log']
        }
      };

      const result = validator.validate(lowRisk);
      expect(result.valid).toBe(true);
    });
  });

  describe('❌ 坏 package 会被明确拒绝', () => {
    test('缺少必需字段: id', () => {
      const bad = {
        version: '0.1.0'
        // 缺少 id, input_schema, etc.
      };

      const result = validator.validate(bad);
      expect(result.valid).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors?.some(e => e.field.includes('id'))).toBe(true);
    });

    test('高风险但没有审批要求', () => {
      const bad = {
        id: 'high_risk_no_approval_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {}
        },
        
        output_schema: {
          type: 'object',
          properties: {}
        },
        
        required_capabilities: {
          platform: ['win_yingdao'],
          tools: ['flow_runner'],
          min_versions: {}
        },
        
        supported_worker_types: ['win_yingdao'],
        
        governance: {
          risk_level: 'high',
          requires_approval_for_write: false,  // ❌ 高风险必须有审批
          max_execution_time_sec: 300
        },
        
        failure_handling: {
          fallback_strategy: 'manual',
          max_retries: 2
        },
        
        execution: {
          timeout_ms: 300000,
          heartbeat_interval_ms: 10000
        },
        
        artifacts: {
          required_artifacts: ['log']
        }
      };

      const result = validator.validate(bad);
      expect(result.valid).toBe(false);
      expect(result.errors?.find(e => e.field === 'governance.requires_approval_for_write')?.message).toContain('must require approval');
    });

    test('没有支持的 worker 类型', () => {
      const bad = {
        id: 'no_worker_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {}
        },
        
        output_schema: {
          type: 'object',
          properties: {}
        },
        
        required_capabilities: {
          platform: ['linux'],
          tools: ['shell'],
          min_versions: {}
        },
        
        supported_worker_types: [],  // ❌ 至少一个
        
        governance: {
          risk_level: 'low',
          requires_approval_for_write: false,
          max_execution_time_sec: 60
        },
        
        failure_handling: {
          fallback_strategy: 'fail_fast',
          max_retries: 0
        },
        
        execution: {
          timeout_ms: 60000,
          heartbeat_interval_ms: 5000
        },
        
        artifacts: {
          required_artifacts: ['log']
        }
      };

      const result = validator.validate(bad);
      expect(result.valid).toBe(false);
      expect(result.errors?.find(e => e.field === 'supported_worker_types')?.message).toContain('At least one');
    });

    test('input_schema 为空', () => {
      const bad = {
        id: 'empty_input_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {}  // ❌ 至少一个属性
        },
        
        output_schema: {
          type: 'object',
          properties: {
            done: {type: 'boolean'}
          }
        },
        
        required_capabilities: {
          platform: ['linux'],
          tools: ['shell'],
          min_versions: {}
        },
        
        supported_worker_types: ['linux'],
        
        governance: {
          risk_level: 'low',
          requires_approval_for_write: false,
          max_execution_time_sec: 60
        },
        
        failure_handling: {
          fallback_strategy: 'fail_fast',
          max_retries: 0
        },
        
        execution: {
          timeout_ms: 60000,
          heartbeat_interval_ms: 5000
        },
        
        artifacts: {
          required_artifacts: ['log']
        }
      };

      const result = validator.validate(bad);
      expect(result.valid).toBe(false);
      expect(result.errors?.find(e => e.field === 'input_schema')?.message).toContain('at least one');
    });

    test('缺少 log 产物', () => {
      const bad = {
        id: 'no_log_artifact_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {
            task_name: {type: 'string'}
          }
        },
        
        output_schema: {
          type: 'object',
          properties: {
            done: {type: 'boolean'}
          }
        },
        
        required_capabilities: {
          platform: ['linux'],
          tools: ['shell'],
          min_versions: {}
        },
        
        supported_worker_types: ['linux'],
        
        governance: {
          risk_level: 'low',
          requires_approval_for_write: false,
          max_execution_time_sec: 60
        },
        
        failure_handling: {
          fallback_strategy: 'fail_fast',
          max_retries: 0
        },
        
        execution: {
          timeout_ms: 60000,
          heartbeat_interval_ms: 5000
        },
        
        artifacts: {
          required_artifacts: ['screenshot']  // ❌ 必须包含 log
        }
      };

      const result = validator.validate(bad);
      expect(result.valid).toBe(false);
      expect(result.errors?.find(e => e.field === 'artifacts.required_artifacts')?.message).toContain('Must include "log"');
    });

    test('超时时间超过上限', () => {
      const bad = {
        id: 'timeout_too_long_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {
            task_name: {type: 'string'}
          }
        },
        
        output_schema: {
          type: 'object',
          properties: {
            done: {type: 'boolean'}
          }
        },
        
        required_capabilities: {
          platform: ['linux'],
          tools: ['shell'],
          min_versions: {}
        },
        
        supported_worker_types: ['linux'],
        
        governance: {
          risk_level: 'low',
          requires_approval_for_write: false,
          max_execution_time_sec: 60
        },
        
        failure_handling: {
          fallback_strategy: 'fail_fast',
          max_retries: 0
        },
        
        execution: {
          timeout_ms: 9999999,  // ❌ 超过 3600000
          heartbeat_interval_ms: 5000
        },
        
        artifacts: {
          required_artifacts: ['log']
        }
      };

      const result = validator.validate(bad);
      expect(result.valid).toBe(false);
      expect(result.errors?.find(e => e.field === 'execution.timeout_ms')?.message).toContain('between');
    });

    test('重试次数超过 10', () => {
      const bad = {
        id: 'too_many_retries_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {
            task_name: {type: 'string'}
          }
        },
        
        output_schema: {
          type: 'object',
          properties: {
            done: {type: 'boolean'}
          }
        },
        
        required_capabilities: {
          platform: ['linux'],
          tools: ['shell'],
          min_versions: {}
        },
        
        supported_worker_types: ['linux'],
        
        governance: {
          risk_level: 'low',
          requires_approval_for_write: false,
          max_execution_time_sec: 60
        },
        
        failure_handling: {
          fallback_strategy: 'retry',
          max_retries: 15  // ❌ 超过 10
        },
        
        execution: {
          timeout_ms: 60000,
          heartbeat_interval_ms: 5000
        },
        
        artifacts: {
          required_artifacts: ['log']
        }
      };

      const result = validator.validate(bad);
      expect(result.valid).toBe(false);
      expect(result.errors?.find(e => e.field === 'failure_handling.max_retries')?.message).toContain('between 0 and 10');
    });
  });

  describe('🔍 边界情况', () => {
    test('最小有效 package', () => {
      const minimal = {
        id: 'minimal_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {
            x: {type: 'string'}
          }
        },
        
        output_schema: {
          type: 'object',
          properties: {
            done: {type: 'boolean'}
          }
        },
        
        required_capabilities: {
          platform: ['linux'],
          tools: ['shell'],
          min_versions: {}
        },
        
        supported_worker_types: ['linux'],
        
        governance: {
          risk_level: 'low',
          requires_approval_for_write: false,
          max_execution_time_sec: 60
        },
        
        failure_handling: {
          fallback_strategy: 'fail_fast',
          max_retries: 0
        },
        
        execution: {
          timeout_ms: 1000,  // 最小值
          heartbeat_interval_ms: 1000
        },
        
        artifacts: {
          required_artifacts: ['log']  // 最小集
        }
      };

      const result = validator.validate(minimal);
      expect(result.valid).toBe(true);
    });

    test('包含可选字段 (metadata)', () => {
      const withMetadata = {
        id: 'with_metadata_v0',
        version: '0.1.0',
        
        input_schema: {
          type: 'object',
          properties: {
            x: {type: 'string'}
          }
        },
        
        output_schema: {
          type: 'object',
          properties: {
            done: {type: 'boolean'}
          }
        },
        
        required_capabilities: {
          platform: ['linux'],
          tools: ['shell'],
          min_versions: {}
        },
        
        supported_worker_types: ['linux'],
        
        governance: {
          risk_level: 'low',
          requires_approval_for_write: false,
          max_execution_time_sec: 60
        },
        
        failure_handling: {
          fallback_strategy: 'fail_fast',
          max_retries: 0
        },
        
        execution: {
          timeout_ms: 60000,
          heartbeat_interval_ms: 5000
        },
        
        artifacts: {
          required_artifacts: ['log']
        },
        
        // 可选字段 - 不影响验证
        metadata: {
          author: 'test',
          quality_metrics: {success_rate: 0.95}
        }
      };

      const result = validator.validate(withMetadata);
      expect(result.valid).toBe(true);
    });
  });
});
