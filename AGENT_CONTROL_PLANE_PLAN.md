# Agent Control Plane 18天实施计划

> **创建时间**: 2026-03-31 14:30
> **分支**: feature/agent-control-plane
> **模型**: glm-5.1

---

## 项目定位

**不做**万能AI，**做**可治理的AI调度中枢 + 专业Agent工厂 v0

**三层架构**:
```
客户入口(私人管家agent) 
    ↓
调度中心(control plane) 
    ↓
专业agent/worker
```

---

## 18天交付目标

1. ✅ 控制平面 v0
2. ✅ 影刀执行底座 v0
3. ✅ OpenClaw/通用 agent worker 接口
4. ✅ 专业 agent package 规范
5. ✅ 2个可复用的专业 agent 模板

---

## 核心抽象(3个对象)

### 1. Task (任务)
**定义**: 一次任务实例
**职责**: 派单

**Schema**:
```typescript
interface Task {
  id: string;
  type: string;  // 对应 agent package 类型
  input: any;    // 符合 agent package 的 input schema
  status: 'pending' | 'running' | 'completed' | 'failed' | 'approval_required';
  worker_id?: string;
  agent_package_id: string;
  created_at: timestamp;
  updated_at: timestamp;
  result?: any;
  error?: string;
  requires_approval: boolean;
  approval_status?: 'pending' | 'approved' | 'rejected';
}
```

### 2. Agent Package (专业Agent包)
**定义**: 可复制、可分享、可配置的专业 agent 模板
**职责**: 做法

**Schema**:
```typescript
interface AgentPackage {
  id: string;
  name: string;
  description: string;
  version: string;
  
  // 输入输出
  input_schema: JSONSchema;
  output_schema: JSONSchema;
  
  // 执行
  required_capabilities: string[];  // 需要的能力(影刀/浏览器/文件系统等)
  supported_worker_types: WorkerType[];
  
  // 治理
  risk_level: 'low' | 'medium' | 'high';
  requires_approval_for_write: boolean;
  failure_fallback: 'retry' | 'manual' | 'skip';
  
  // 元数据
  author: string;
  tags: string[];
  created_at: timestamp;
  updated_at: timestamp;
}
```

### 3. Worker (执行器)
**定义**: 真正干活的执行器
**职责**: 执行腿脚

**Schema**:
```typescript
interface Worker {
  id: string;
  name: string;
  type: 'openclaw' | 'linux' | 'mac' | 'win_yingdao';
  status: 'online' | 'offline' | 'busy';
  capabilities: string[];
  current_task_id?: string;
  last_heartbeat: timestamp;
}

interface WorkerType {
  name: string;
  execute(task: Task): Promise<TaskResult>;
  get_status(): Promise<WorkerStatus>;
  cancel(task_id: string): Promise<void>;
}
```

---

## 一句话定锚

**task 是派单，agent package 是做法，worker 是执行腿脚**

---

## 18天排期

### Day 1-2: 冻结核心抽象

**目标**: 定死3个对象的定义和边界

**任务**:
- [ ] 创建项目结构
- [ ] 定义 TypeScript 接口(Task/AgentPackage/Worker)
- [ ] 创建数据模型(数据库schema)
- [ ] 写清楚"一句话定锚"文档
- [ ] 确认3个对象的职责边界

**交付**:
- 完整的类型定义文件
- 数据库migration文件
- 核心抽象文档

**验收标准**:
- 3个对象的定义不再变化
- 职责边界清晰，没有灰色地带
- 文档能让新人5分钟理解架构

---

### Day 3-4: 影刀执行底座

**目标**: 把影刀抽成平台能力

**任务**:
- [ ] 设计影刀 worker 接口
- [ ] 实现 `run_flow(flow_id, inputs)`
- [ ] 实现 `get_run_status(run_id)`
- [ ] 实现 `get_artifacts(run_id)`
- [ ] 实现 `cancel_run(run_id)`
- [ ] 写第一个影刀 flow 示例

**接口设计**:
```typescript
interface YingdaoWorker {
  run_flow(flow_id: string, inputs: Record<string, any>): Promise<RunId>;
  get_run_status(run_id: string): Promise<RunStatus>;
  get_artifacts(run_id: string): Promise<Artifact[]>;
  cancel_run(run_id: string): Promise<void>;
}

interface RunStatus {
  run_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  started_at: timestamp;
  completed_at?: timestamp;
  error?: string;
}

interface Artifact {
  type: 'screenshot' | 'log' | 'file' | 'receipt';
  path: string;
  metadata: Record<string, any>;
}
```

**交付**:
- YingdaoWorker 接口实现
- 第一个 flow 示例
- 接口文档

**验收标准**:
- 能通过代码调用影刀 flow
- 能获取执行状态和结果
- 能取消正在运行的 flow

---

### Day 5-6: Agent Package 规范

**目标**: 定义可复用的专业 agent 包规范

**任务**:
- [ ] 定义 AgentPackage JSON Schema
- [ ] 实现 Agent Package Registry(存储/查询)
- [ ] 实现 Agent Package 验证器
- [ ] 写第一个 agent package 模板
- [ ] 写 agent package 创建/更新/删除 API

**Agent Package 示例**:
```json
{
  "id": "yingdao_form_fill_agent",
  "name": "影刀表单录入 Agent",
  "description": "自动录入客户信息到ERP系统",
  "version": "0.1.0",
  
  "input_schema": {
    "type": "object",
    "properties": {
      "customer_name": {"type": "string"},
      "order_id": {"type": "string"},
      "amount": {"type": "number"}
    },
    "required": ["customer_name", "order_id", "amount"]
  },
  
  "output_schema": {
    "type": "object",
    "properties": {
      "receipt": {"type": "string"},
      "screenshots": {"type": "array"},
      "logs": {"type": "array"}
    }
  },
  
  "required_capabilities": ["yingdao_flow"],
  "supported_worker_types": ["win_yingdao"],
  
  "risk_level": "high",
  "requires_approval_for_write": true,
  "failure_fallback": "manual"
}
```

**交付**:
- AgentPackage JSON Schema
- Agent Package Registry 实现
- Package 验证器
- 2个 package 示例

**验收标准**:
- 能创建/注册 agent package
- 能验证 package 格式正确性
- 能查询符合条件的 package
- 示例 package 能被加载和执行

---

### Day 7-8: 最小控制台

**目标**: 做 agent 包管理界面

**页面**:
1. **Agent Packages 页面**
   - 注册新 package
   - 启停 package
   - 版本标记
   - 查看 schema
   - 查看支持的 worker
   - 手动发起测试任务

2. **Tasks 页面**
   - 任务列表
   - 任务详情
   - 任务状态

3. **Workers 页面**
   - Worker 状态
   - Worker 注册

**任务**:
- [ ] 设计控制台 UI(简版)
- [ ] 实现 Agent Packages CRUD API
- [ ] 实现 Tasks CRUD API
- [ ] 实现 Workers 监控 API
- [ ] 写前端页面(单页应用)

**交付**:
- 控制台后端 API
- 控制台前端页面
- API 文档

**验收标准**:
- 能通过界面管理 agent packages
- 能查看任务和 worker 状态
- 能手动发起测试任务

---

### Day 9-10: 接通用worker

**目标**: 先建立通用 agent 能力层

**顺序**:
1. **Linux Worker** (最稳)
2. **OpenClaw Worker** (成熟通用 agent runtime)
3. **Win+影刀 Worker** (专业业务执行)

**任务**:
- [ ] 设计通用 worker 接口
- [ ] 实现 Linux worker
- [ ] 实现 OpenClaw worker
- [ ] 实现 worker 注册/心跳机制
- [ ] 实现 worker 调度器

**Linux Worker 接口**:
```typescript
interface LinuxWorker {
  execute_command(command: string): Promise<CommandResult>;
  execute_script(script: string): Promise<ScriptResult>;
  get_status(): Promise<WorkerStatus>;
}
```

**OpenClaw Worker 接口**:
```typescript
interface OpenClawWorker {
  send_message(message: string): Promise<MessageResult>;
  run_skill(skill: string, params: any): Promise<SkillResult>;
  get_status(): Promise<WorkerStatus>;
}
```

**交付**:
- Linux worker 实现
- OpenClaw worker 实现
- Worker 注册/心跳机制
- Worker 调度器

**验收标准**:
- Linux worker 能执行命令和脚本
- OpenClaw worker 能发送消息和运行 skill
- Worker 能注册和心跳
- 调度器能把任务分发给 worker

---

### Day 11-12: 第一类专业agent

**目标**: 打通完整流程

**选择**: 录入类 agent 或 对账回填类 agent

**流程**:
```
控制平面选中 agent package
    ↓
agent package 校验输入
    ↓
调度到 win_yingdao_worker
    ↓
调用固定 flow
    ↓
回传截图/日志/回执
    ↓
gate 判定是否完成
```

**任务**:
- [ ] 选择第一类 agent(录入类)
- [ ] 创建 agent package
- [ ] 写影刀 flow
- [ ] 实现完整执行流程
- [ ] 实现 gate 判定逻辑
- [ ] 测试端到端流程

**交付**:
- 第一个专业 agent package
- 对应的影刀 flow
- 完整执行流程代码
- 测试报告

**验收标准**:
- 能从控制台发起任务
- agent 能正确执行
- 能回传结果和截图
- gate 能正确判定

---

### Day 13-14: 第二类专业agent

**目标**: 验证可复制性

**选择**: 报表下载并归档 agent

**要求**:
- 必须复用前面的规范
- 只改配置和少量逻辑
- 1天内完成

**任务**:
- [ ] 选择第二类 agent
- [ ] 基于 agent package 模板创建
- [ ] 写对应的 flow
- [ ] 测试端到端流程
- [ ] 对比两个 agent 的代码重复度

**交付**:
- 第二个专业 agent package
- 对应的 flow
- 复用性分析报告

**验收标准**:
- 第二个 agent 能正常工作
- 代码重复度 > 80%
- 只改配置和少量逻辑

---

### Day 15-16: 补上线能力

**目标**: 做上线必备功能

**任务**:
- [ ] 高风险 agent 审批流程
- [ ] 任务回放功能
- [ ] 失败重试机制
- [ ] agent package 导出/导入
- [ ] 基础版本号管理

**审批流程设计**:
```typescript
interface ApprovalProcess {
  task: Task;
  requires_approval: boolean;
  approvers: string[];
  status: 'pending' | 'approved' | 'rejected';
  comments?: string;
}
```

**重试机制**:
```typescript
interface RetryPolicy {
  max_retries: number;
  retry_delay: number;
  retry_on_errors: string[];
}
```

**交付**:
- 审批流程实现
- 任务回放功能
- 失败重试机制
- Package 导出/导入工具
- 版本号管理

**验收标准**:
- 高风险任务必须审批才能执行
- 能回放历史任务
- 失败任务能自动重试
- Package 能导出和导入

---

### Day 17-18: 最小自优化

**目标**: 只优化路由和模板选择

**优化对象**:
- ✅ 哪类任务优先推荐哪个 agent package
- ✅ 哪个 worker 执行成功率更高
- ✅ 哪种失败该 retry，哪种该转人工
- ✅ 哪个模板版本更稳定

**不优化**:
- ❌ 权限
- ❌ gate
- ❌ 影刀流程本身
- ❌ package 的核心风险规则

**任务**:
- [ ] 设计优化指标收集
- [ ] 实现路由推荐算法
- [ ] 实现 worker 成功率统计
- [ ] 实现失败分类和重试策略
- [ ] 实现 A/B 测试框架

**优化指标**:
```typescript
interface OptimizationMetrics {
  task_type: string;
  agent_package_id: string;
  worker_id: string;
  success_rate: number;
  avg_duration: number;
  retry_count: number;
}
```

**交付**:
- 优化指标收集
- 路由推荐算法
- 统计看板
- A/B 测试框架

**验收标准**:
- 系统能推荐最优的 agent package
- 能选择成功率最高的 worker
- 能智能判断是否重试
- 能比较不同版本的效果

---

## 技术栈

### 后端
- **语言**: TypeScript/Node.js
- **数据库**: SQLite(开发) / PostgreSQL(生产)
- **ORM**: Prisma
- **API**: REST + WebSocket(实时更新)

### 前端
- **框架**: React + TypeScript
- **UI库**: shadcn/ui
- **状态管理**: Zustand
- **实时**: WebSocket

### Worker
- **Linux**: SSH + child_process
- **OpenClaw**: OpenClaw API
- **影刀**: 影刀 API

### 部署
- **开发**: Docker Compose
- **生产**: 待定

---

## 项目结构

```
agent-control-plane/
├── packages/
│   ├── core/                    # 核心抽象
│   │   ├── src/
│   │   │   ├── task/            # Task 模型
│   │   │   ├── agent-package/   # AgentPackage 模型
│   │   │   └── worker/          # Worker 模型
│   │   └── package.json
│   │
│   ├── api/                     # 后端 API
│   │   ├── src/
│   │   │   ├── routes/          # API 路由
│   │   │   ├── services/        # 业务逻辑
│   │   │   └── db/              # 数据库
│   │   └── package.json
│   │
│   ├── workers/                 # Worker 实现
│   │   ├── linux/               # Linux worker
│   │   ├── openclaw/            # OpenClaw worker
│   │   └── yingdao/             # 影刀 worker
│   │
│   ├── console/                 # 控制台前端
│   │   ├── src/
│   │   │   ├── pages/           # 页面
│   │   │   ├── components/      # 组件
│   │   │   └── lib/             # 工具
│   │   └── package.json
│   │
│   └── agent-packages/          # 专业 agent 包
│       ├── form-fill/           # 表单录入 agent
│       └── report-download/     # 报表下载 agent
│
├── docs/                        # 文档
│   ├── architecture.md          # 架构文档
│   ├── api.md                   # API 文档
│   └── agent-package-spec.md    # Agent Package 规范
│
├── scripts/                     # 脚本
│   ├── setup.sh                 # 初始化脚本
│   └── dev.sh                   # 开发环境启动
│
└── README.md                    # 项目说明
```

---

## 客户入口层(私人管家agent)

**注意**: 这部分不在18天内实现，但架构上要预留

**定位**: 前台门面，让客户愿意用

**职责**:
1. 任务理解(自然语言 → 结构化任务)
2. 偏好记忆(常用系统/模板/审批习惯)
3. 汇报与确认(高风险前确认，完成后回报)
4. 任务入口统一(客户只面对一个"管家")

**实现方式**:
- 用 OpenClaw 现成做前台人格和聊天入口
- 只加"任务翻译器"
- 让它把用户意图转成标准任务单
- 交给 control plane

**不做**:
- 长期人格宇宙
- 多agent互相辩论
- 自己改自己
- 完整CRM/ERP前台
- 再造一套skills生态

---

## 砍掉的功能

- ❌ 私人管家人格化(移到客户入口层)
- ❌ 长期记忆人格
- ❌ 全自动自我进化
- ❌ 多agent自主辩论
- ❌ 通用万能影刀agent
- ❌ "零人公司"完整治理幻想

---

## 成功标准

18天后，系统应该能展示:

1. ✅ 我能注册 worker
2. ✅ 我能注册专业 agent 包
3. ✅ 我能把任务交给指定 agent 包
4. ✅ agent 包能调 OpenClaw / Linux / Win+影刀
5. ✅ 我能审批、回放、看日志
6. ✅ 我能复制一个 agent，稍微改配置就变成另一个

**核心追求**: 不做"更全"，只做2个真的能复用的专业agent

---

## 下一步

等待确认后开始 Day 1-2: 冻结核心抽象
