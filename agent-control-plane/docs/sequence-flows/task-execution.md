# Task Execution Sequence Flow

> **最后更新**: 2026-03-31 15:25
> **状态**: 已冻结

---

## 完整执行流程

```mermaid
sequenceDiagram
    autonumber
    participant User as 用户/前台
    participant CP as Control Plane
    participant Scheduler as 调度器
    participant Worker as Worker
    participant Yingdao as 影刀
    participant ERP as ERP系统

    Note over User,CP: 1. 任务创建

    User->>CP: 创建任务 (task.input)
    CP->>CP: 验证 input (input_schema)
    CP->>CP: 检查审批要求
    alt 需要审批
        CP->>User: 请求审批
        User->>CP: 批准/拒绝
        alt 拒绝
            CP-->>User: 任务已拒绝
        end
    end

    Note over CP,Scheduler: 2. 任务调度

    CP->>Scheduler: 提交任务
    Scheduler->>Scheduler: 选择 Worker
    Scheduler->>Worker: startTask(task, options)

    Note over Worker,Yingdao: 3. 任务执行

    Worker->>Yingdao: runFlow(flow_id, inputs)
    Yingdao->>ERP: OpenApp
    Yingdao->>ERP: NavigateTo
    Yingdao->>ERP: FillForm
    Yingdao->>ERP: ClickButton

    loop 心跳查询 (每10秒)
        Worker->>Yingdao: queryStatus(run_id)
        Yingdao-->>Worker: status(progress)
        Worker-->>Scheduler: heartbeat(status)
        Scheduler-->>CP: 任务状态更新
    end

    alt 执行成功
        Yingdao->>Yingdao: Screenshot
        Yingdao->>Yingdao: ExtractReceipt
        Yingdao-->>Worker: completed(result, artifacts)
        Worker->>Worker: classifyArtifacts(artifacts)
        Worker-->>Scheduler: completed
        Scheduler-->>CP: 任务完成
        CP->>CP: 更新质量指标
        CP-->>User: 任务完成 (result)
    else 执行失败
        Yingdao->>Yingdao: CaptureError
        Yingdao-->>Worker: failed(error, screenshot)
        Worker->>Worker: classifyError(error)
        alt 可重试
            Worker->>Worker: applyRetryPolicy(error)
            Worker->>Yingdao: retryFlow()
        else 不可重试
            Worker-->>Scheduler: failed(classification)
            Scheduler-->>CP: 任务失败
            CP->>CP: 记录失败原因
            CP-->>User: 任务失败 (建议转人工)
        end
    end
```

---

## 关键决策点

### 1. 输入验证

```mermaid
graph TD
    A[接收任务] --> B{验证 input_schema}
    B -->|通过| C[继续]
    B -->|失败| D[返回错误]
    C --> E{检查审批要求}
    E -->|需要审批| F[请求审批]
    E -->|不需要| G[调度任务]
    F --> H{审批结果}
    H -->|批准| G
    H -->|拒绝| I[任务已拒绝]
```

### 2. 错误处理

```mermaid
graph TD
    A[任务失败] --> B[分类错误]
    B --> C{错误类型}
    C -->|瞬时错误| D{可重试?}
    C -->|永久错误| E[转人工]
    C -->|业务错误| F[需要判断]
    D -->|是| G[重试]
    D -->|否| E
    G --> H{重试次数}
    H -->|未超限| I[继续重试]
    H -->|超限| J[升级处理]
    F --> K{建议}
    K -->|跳过| L[记录并继续]
    K -->|人工| E
```

### 3. 产物收集

```mermaid
graph LR
    A[任务完成] --> B[收集产物]
    B --> C{产物类型}
    C -->|screenshot| D[验证PNG格式]
    C -->|log| E[验证JSON格式]
    C -->|receipt| F[验证回执完整性]
    D --> G[存储到S3]
    E --> G
    F --> G
    G --> H[更新任务结果]
```

---

## 数据流

### 输入数据

```
User (前台)
  → {customer_name: "张三", order_id: "ORD20260331", amount: 1500.00}
  → Control Plane (验证 input_schema)
  → Scheduler (选择 Worker)
  → Worker (准备 options)
  → Yingdao (执行 flow)
  → ERP (录入数据)
```

### 输出数据

```
ERP (回执)
  → Yingdao (提取 receipt)
  → Worker (包装 artifacts)
  → Scheduler (更新状态)
  → Control Plane (记录质量指标)
  → User (返回结果)
  → {success: true, receipt: {...}, artifacts: [...]}
```

---

## 错误流

### 瞬时错误 (可重试)

```
NETWORK_ERROR
  → Worker (classifyError)
  → {category: 'transient', retryable: true}
  → Worker (applyRetryPolicy)
  → retry after 5000ms
  → Yingdao (retryFlow)
```

### 永久错误 (需人工)

```
ELEMENT_NOT_FOUND
  → Worker (classifyError)
  → {category: 'permanent', retryable: false}
  → Worker (不重试)
  → Scheduler (转人工)
  → Control Plane (记录原因)
  → User (通知转人工)
```

### 业务错误 (需判断)

```
DUPLICATE_RECORD
  → Worker (classifyError)
  → {category: 'business', suggested_action: 'skip'}
  → Worker (跳过)
  → Scheduler (标记完成)
  → Control Plane (记录)
  → User (通知记录已存在)
```

---

## 性能指标

### 关键时间点

| 时间点 | 说明 | 预期值 |
|--------|------|--------|
| 创建到调度 | 任务进入队列 | < 1s |
| 调度到启动 | Worker 开始执行 | < 5s |
| 启动到完成 | 任务执行完成 | ~15s |
| 心跳间隔 | 状态查询频率 | 10s |
| 完整流程 | 端到端时间 | < 30s |

### 质量指标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 成功率 | ≥ 95% | - |
| 平均执行时间 | ≤ 20s | - |
| 重试率 | ≤ 10% | - |
| 审批通过率 | ≥ 80% | - |

---

## 验收标准

- [ ] Sequence diagram 完整描述执行流程
- [ ] 所有关键决策点都有标注
- [ ] 数据流清晰可追踪
- [ ] 错误流处理完整
- [ ] 性能指标有明确目标

---

## 下一步

- [ ] 实现调度器
- [ ] 实现 Worker
- [ ] 实现错误分类器
- [ ] 写单元测试
