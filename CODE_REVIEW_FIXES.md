# Day 3-4: 修正清单

> **评分**: 8.7/10
> **状态**: Day 1-2 通过，Day 3-4 完成 70-80%
> **下一步**: 补测试，统一口径

---

## Code Review 清单

### 🔴 必须马上改 (半天内)

#### 1. classifyError 签名不一致
**问题**: contract.ts 是同步，mock.ts 是 async
```typescript
// contract.ts
classifyError(error: Error): YingdaoErrorClassification;

// mock.ts
async classifyError(error: Error): Promise<YingdaoErrorClassification>
```

**修复**: 统一成同步
```typescript
// contract.ts
classifyError(error: Error): YingdaoErrorClassification;

// mock.ts
classifyError(error: Error): YingdaoErrorClassification {
  // 移除 async
}
```

---

#### 2. artifact 最小集不一致
**问题**: 文档说 4 个，实现只有 3 个
```
文档: run.log + summary.json + final_screenshot.png + receipt.json
实现: log + screenshot + receipt (少 summary)
```

**修复**: 实现 4 个 artifact
```typescript
async getArtifacts(handle: YingdaoTaskHandle): Promise<YingdaoArtifact[]> {
  return [
    {
      type: 'log',
      path: '/artifacts/mock-run.log',
      // ...
    },
    {
      type: 'metadata',  // summary 改为 metadata
      path: '/artifacts/mock-summary.json',
      // ...
    },
    {
      type: 'screenshot',
      path: '/artifacts/mock-final.png',
      // ...
    },
    {
      type: 'receipt',
      path: '/artifacts/mock-receipt.json',
      // ...
    }
  ];
}
```

---

#### 3. 移除未使用字段
**问题**: `private currentStep = 0` 定义但未使用

**修复**: 删除该字段
```typescript
// 删除这行
- private currentStep = 0;
```

---

### 🟡 可以后补 (Day 5-6)

#### 4. manifest 字段标注
**问题**: manifest 太满，没区分 runtime_required 和 metadata_optional

**修复**: 添加字段分类
```json
{
  "runtime_required": {
    "id": "...",
    "name": "...",
    "version": "...",
    "input_schema": {...},
    "output_schema": {...},
    "required_capabilities": {...},
    "supported_worker_types": [...],
    "governance": {...},
    "failure_handling": {...}
  },
  "metadata_optional": {
    "metadata": {
      "author": "...",
      "license": "...",
      "tags": [...],
      "documentation": {...},
      "quality_metrics": {...}
    },
    "compatibility": {...},
    "observability": {...}
  }
}
```

---

### 🟢 先别碰 (Day 7-8 之后)

#### 5. 真实影刀接入
**状态**: 等测试通过后再接

#### 6. 完整 UI
**状态**: 等核心稳定后再做

---

## 测试清单

### 📝 必须完成 (今天)

#### 1. classifyError.test.ts
覆盖 8+ 错误场景:
- [ ] ECONNREFUSED / NETWORK → transient, retryable
- [ ] AUTH_FAILED → permanent, manual
- [ ] FLOW_NOT_FOUND → permanent, manual
- [ ] INVALID_INPUT / VALIDATION → business, manual
- [ ] ELEMENT_NOT_FOUND → permanent, manual
- [ ] TIMEOUT → transient, retryable
- [ ] DUPLICATE_RECORD → business, skip
- [ ] ARTIFACT_MISSING / UNKNOWN → system, escalate

---

#### 2. e2e.test.ts
完整流程测试:
- [ ] 创建 Task
- [ ] startTask
- [ ] 轮询到 completed
- [ ] getArtifacts (校验 4 个)
- [ ] cancelRun 分支

---

## 修复优先级

| 优先级 | 任务 | 时间 |
|--------|------|------|
| P0 | classifyError 签名统一 | 5分钟 |
| P0 | artifact 最小集补齐 | 10分钟 |
| P0 | 移除未使用字段 | 2分钟 |
| P1 | classifyError 测试 | 30分钟 |
| P1 | E2E 测试 | 30分钟 |
| P2 | manifest 字段标注 | 15分钟 |

**总时间**: ~1.5 小时

---

## 下一步行动

1. ✅ 修复接口不一致 (17分钟)
2. ✅ 写 classifyError.test.ts (30分钟)
3. ✅ 写 e2e.test.ts (30分钟)
4. ✅ 运行测试验证
5. ✅ 提交修正版

**目标**: 今天内完成，达到 9.0/10
