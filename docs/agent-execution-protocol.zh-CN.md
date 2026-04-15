# Agent Execution Protocol (AEP v0)

## 目标

AEP v0 让每个 agent 成为 **driver adapter** 而不是 control plane。

## 核心原则

### 1. Agent 不拥有仓库写权限

Agent 可以生成补丁，但不能直接提交。所有代码变更必须经过验证和晋升流程。

### 2. 执行隔离

Agent 在隔离环境中执行，无法访问超出其权限范围的资源。

### 3. 可审计的输出

Agent 的所有操作都必须可审计，包括生成的补丁、执行的命令等。

## 执行流程

```
任务创建 → Agent 执行 → 补丁生成 → 验证 → 晋升 → 发布
```

### 1. 任务创建

Control plane 创建任务，指定：
- 任务类型
- 执行约束
- 验证规则
- 晋升条件

### 2. Agent 执行

Agent 在隔离环境中执行任务：
- 读取任务描述
- 执行必要的操作
- 生成补丁或结果

### 3. 补丁生成

Agent 生成补丁文件：
- 只包含必要的变更
- 不包含运行时产物
- 符合补丁格式规范

### 4. 验证

验证补丁：
- 代码质量检查
- 安全扫描
- 功能测试

### 5. 晋升

如果验证通过：
- 补丁晋升为草稿 PR
- 通知相关人员进行审查
- 等待最终批准

### 6. 发布

批准后：
- 合并到目标分支
- 更新相关文档
- 触发后续流程

## Agent 接口

### 输入

```json
{
  "task_id": "string",
  "task_type": "string",
  "description": "string",
  "constraints": {
    "max_execution_time": "number",
    "allowed_operations": ["string"]
  },
  "context": {
    "repository": "string",
    "branch": "string",
    "base_commit": "string"
  }
}
```

### 输出

```json
{
  "task_id": "string",
  "status": "success|failure",
  "patch": {
    "files": [
      {
        "path": "string",
        "changes": "string"
      }
    ]
  },
  "metadata": {
    "execution_time": "number",
    "operations_performed": ["string"]
  }
}
```

## 安全考虑

1. **最小权限原则**：Agent 只拥有完成任务所需的最小权限
2. **沙箱执行**：Agent 在沙箱环境中执行
3. **输出验证**：所有输出都经过验证
4. **审计日志**：记录所有操作

## 与 OpenHands 集成

详见 [OpenHands 集成指南](./openhands-cli-integration.zh-CN.md)。
