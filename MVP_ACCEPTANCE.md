# MVP Acceptance Criteria

> **分支**: feature/control-plane-v0-sprint18
> **时间**: 2026-03-31 15:15
> **目标**: 把口头设计变成硬文件

---

## 验收原则

**自查 ≠ 验收**

自查回答"能不能做"，验收回答"做没做好"。

---

## Day 1-2 验收标准

### ✅ 硬文件清单

- [x] **Task / AgentPackage / Worker 类型定义** (TypeScript 接口)
  - 位置: `agent-control-plane/packages/core/src/types/`
  - 文件:
    - [x] `task.ts`
    - [x] `agent-package.ts`
    - [x] `worker.ts`
    - [x] `index.ts`
  - 验收: 能 import 并使用所有类型

- [ ] **WinYingdaoWorkerContract 接口** (真实接口文档)
  - 位置: `agent-control-plane/docs/worker-contracts/yingdao-worker.md`
  - 内容:
    - [ ] 5个核心方法签名
    - [ ] 输入输出数据结构
    - [ ] 错误分类清单(15+ 种)
    - [ ] Sequence diagram
  - 验收: 能照着文档实现一个 worker

- [ ] **Agent Package 示例** (真实 manifest)
  - 位置: `agent-control-plane/packages/agent-packages/form-fill/`
  - 内容:
    - [ ] `manifest.json` (完整)
    - [ ] `schema/input.json`
    - [ ] `schema/output.json`
    - [ ] `README.md` (使用说明)
  - 验收: 能通过 validator 验证

- [ ] **Monorepo 目录骨架**
  - 位置: `agent-control-plane/`
  - 结构:
    - [ ] `packages/core/` (核心类型)
    - [ ] `packages/api/` (后端 API)
    - [ ] `packages/workers/` (Worker 实现)
    - [ ] `packages/console/` (控制台前端)
    - [ ] `packages/agent-packages/` (Agent 包)
    - [ ] `docs/` (文档)
    - [ ] `scripts/` (脚本)
  - 验收: 目录结构符合 plan

- [ ] **MVP_ACCEPTANCE.md** (本文件)
  - 验收: 每个条目都能打勾

---

## Day 1-2 之后必须看到的证据

### 1. Manifest 的真实字段定义

**不是**:
- ❌ 说"应该有输入输出 schema"
- ❌ 说"应该有治理规则"

**而是**:
- ✅ 真实的 `AgentPackage` interface
- ✅ 每个字段都有明确的类型
- ✅ 每个字段都有文档说明
- ✅ 有完整的 TypeScript 类型定义

**证据位置**: `packages/core/src/types/agent-package.ts`

**验证方法**:
```bash
cd agent-control-plane/packages/core
npm install
npm run build
# 应该能成功编译，没有类型错误
```

---

### 2. Worker Contract 的真实接口文档

**不是**:
- ❌ 说"应该有 startTask 方法"
- ❌ 说"应该有错误分类"

**而是**:
- ✅ 真实的 `Worker` interface
- ✅ 每个方法都有签名
- ✅ 每个方法都有参数说明
- ✅ 有完整的错误分类清单
- ✅ 有 sequence diagram 说明执行流程

**证据位置**: `docs/worker-contracts/yingdao-worker.md`

**验证方法**:
- 读完文档能独立实现一个 worker
- 文档和 TypeScript 接口一致
- 有清晰的错误分类规则

---

### 3. 至少一个 Package 示例

**不是**:
- ❌ 说"应该有表单录入 agent"
- ❌ 说"输入是客户信息"

**而是**:
- ✅ 真实的 `manifest.json` 文件
- ✅ 完整的 input/output JSON Schema
- ✅ 明确的治理规则
- ✅ 可运行的示例

**证据位置**: `packages/agent-packages/form-fill/manifest.json`

**验证方法**:
```bash
cd agent-control-plane
node scripts/validate-package.js packages/agent-packages/form-fill/manifest.json
# 应该输出: ✅ Valid
```

---

### 4. 一个最小 Sequence Flow 图

**不是**:
- ❌ 说"任务从创建到完成"
- ❌ 说"worker 调用 flow"

**而是**:
- ✅ 真实的 Mermaid/PlantUML 图
- ✅ 每一步都有明确的参与者
- ✅ 每一步都有明确的输入输出
- ✅ 标注了关键决策点

**证据位置**: `docs/sequence-flows/task-execution.md`

**验证方法**:
- 能看图理解完整流程
- 图和代码一致
- 标注了错误处理路径

---

## 验收检查清单

### 类型定义
- [ ] 所有接口都有完整的 TypeScript 定义
- [ ] 所有字段都有注释
- [ ] 所有枚举都有文档
- [ ] 能成功编译无错误

### 接口文档
- [ ] 每个方法都有签名
- [ ] 每个参数都有类型和说明
- [ ] 每个返回值都有结构
- [ ] 有使用示例

### Agent Package
- [ ] manifest.json 符合 schema
- [ ] 有完整的 input/output schema
- [ ] 有明确的治理规则
- [ ] 有使用说明

### 文档
- [ ] 有架构图
- [ ] 有 sequence diagram
- [ ] 有错误分类清单
- [ ] 有生活类比

### 代码
- [ ] 有 package.json
- [ ] 有 tsconfig.json
- [ ] 有 README.md
- [ ] 有 .gitignore

---

## 口头评审 vs 代码评审

### 口头评审 (已完成)
- ✅ 回答了三个要命问题
- ✅ 有工程脑子
- ✅ 自查通过
- ✅ 值得开工

### 代码评审 (进行中)
- [ ] 看到真实的文件
- [ ] 看到真实的接口
- [ ] 看到真实的示例
- [ ] 看到真实的流程图

---

## 成功标准

**Day 1-2 完成**:
- 不是"听汇报"
- 而是"看真东西"

**具体说**:
- 能打开文件看到真实代码
- 能运行命令验证类型定义
- 能读文档理解架构
- 能看示例明白用法

---

## 下一步

### Day 3-4 开始前必须完成
- [ ] WinYingdaoWorkerContract 接口文档
- [ ] Agent Package 示例 (form-fill)
- [ ] Sequence Flow 图
- [ ] Prisma Schema (数据库模型)

### 验收通过标志
- [ ] 所有硬文件清单打勾
- [ ] 所有证据位置有文件
- [ ] 所有验证方法能通过

---

## 一句话

**口头评审通过 = 值得开工**
**代码评审通过 = 已经做好**

现在状态: **值得开工** ✅
目标状态: **已经做好** ⏳

**最对的动作**: 新建分支，立刻开始 Day 1-2，把口头设计变成硬文件。
