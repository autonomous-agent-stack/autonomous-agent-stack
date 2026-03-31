# 迁移到 autonomous-agent-stack

> **最后更新**: 2026-03-31 16:00
> **源仓库**: openclaw-memory
> **目标仓库**: autonomous-agent-stack

---

## 迁移范围

### 需要迁移的目录和文件

```
agent-control-plane/          # 整个目录
├── docs/                      # 文档
│   ├── sequence-flows/
│   └── worker-contracts/
├── packages/
│   ├── core/                 # 核心类型和验证器
│   │   └── src/
│   │       ├── schemas/
│   │       ├── validation/
│   │       └── __tests__/
│   ├── workers/               # Worker 实现
│   │   └── yingdao/
│   └── agent-packages/        # Agent 包
│       ├── form-fill/
│       └── report-download/

AGENT_CONTROL_PLANE_PLAN.md  # 18天计划
AGENT_PACKAGE_SPEC.md         # Package 规范
WORKER_CONTRACT_SPEC.md       # Worker Contract
AGENT_REUSE_ANALYSIS.md       # 复用性分析

DAY01-02-CHECKLIST.md
DAY03-04-CHECKLIST.md
DAY05-06-CHECKLIST.md
MVP_ACCEPTANCE.md
CODE_REVIEW_FIXES.md
```

---

## 迁移步骤

### Step 1: 复制文件

```bash
# 在 openclaw-memory
cd /Users/iCloud_GZ/github_GZ/openclaw-memory

# 复制到 autonomous-agent-stack
cp -r agent-control-plane /Volumes/AI_LAB/Github/autonomous-agent-stack/
cp AGENT*.md /Volumes/AI_LAB/Github/autonomous-agent-stack/
cp WORKER*.md /Volumes/AI_LAB/Github/autonomous-agent-stack/
cp DAY*.md /Volumes/AI_LAB/Github/autonomous-agent-stack/
cp MVP*.md /Volumes/AI_LAB/Github/autonomous-agent-stack/
cp CODE*.md /Volumes/AI_LAB/Github/autonomous-agent-stack/
```

### Step 2: 切换到目标仓库

```bash
cd /Volumes/AI_LAB/Github/autonomous-agent-stack
git checkout -b feature/agent-control-plane-v0-sprint18
git add agent-control-plane/ AGENT*.md WORKER*.md DAY*.md MVP*.md CODE*.md
git commit -m "Migrate Agent Control Plane from openclaw-memory"
git push -u origin feature/agent-control-plane-v0-sprint18
```

### Step 3: 验证

```bash
# 验证文件结构
ls -la agent-control-plane/packages/
ls -la agent-control-plane/packages/agent-packages/

# 验证测试
cd agent-control-plane/packages/core
npm install
npm test  # AgentPackageValidator.test.ts 必须通过
```

---

## Source of Truth

**Source of Truth**: openclaw-memory/agent-control-plane/

**目标位置**: autonomous-agent-stack/agent-control-plane/

**同步策略**: 先在 openclaw-memory 开发，测试通过后迁移

---

## 注意事项

1. **不要直接在 autonomous-agent-stack 修改**: 先在 openclaw-memory 开发
2. **保持同步**: 每次大进展后迁移一次
3. **测试优先**: 迁移前确保所有测试通过
4. **文档同步**: PLAN/检查清单/文档也要同步

---

## 下一步

Day 5-6 完成后立即执行迁移。
