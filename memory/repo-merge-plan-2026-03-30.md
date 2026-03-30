# 仓库合并计划（2026-03-30 00:10）

## 🎯 目标
减少碎片化仓库，合并相关项目

## 📊 待合并仓库（7 个）

### 合并到 learning-hub（3 个）
1. **movie-commentary-learning**（最后更新：2026-03-23）
2. **apple-learning**（最后更新：2026-03-23）
3. **tesla-ai-learning**（最后更新：2026-03-23）

### 合并到 ai-knowledge-graph（4 个）
1. **ai-security-governance**（最后更新：2026-03-22）
2. **ai-business-automation**（最后更新：2026-03-22）
3. **rag-knowledge-system**（最后更新：2026-03-22）
4. **ai-agent-workflow-engine**（最后更新：2026-03-22）

## 📋 执行步骤

### 阶段 1：检查内容
```bash
# 检查这些仓库是否有实际内容
for repo in movie-commentary-learning apple-learning tesla-ai-learning; do
  echo "=== $repo ==="
  gh repo view srxly888-creator/$repo --json name,description,diskUsage
done
```

### 阶段 2：克隆备份
```bash
# 创建临时目录
mkdir -p /tmp/merge-backup

# 克隆待合并的仓库
gh repo clone srxly888-creator/movie-commentary-learning /tmp/merge-backup/movie-commentary-learning
gh repo clone srxly888-creator/apple-learning /tmp/merge-backup/apple-learning
gh repo clone srxly888-creator/tesla-ai-learning /tmp/merge-backup/tesla-ai-learning
gh repo clone srxly888-creator/ai-security-governance /tmp/merge-backup/ai-security-governance
gh repo clone srxly888-creator/ai-business-automation /tmp/merge-backup/ai-business-automation
gh repo clone srxly888-creator/rag-knowledge-system /tmp/merge-backup/rag-knowledge-system
gh repo clone srxly888-creator/ai-agent-workflow-engine /tmp/merge-backup/ai-agent-workflow-engine
```

### 阶段 3：合并到目标仓库

#### 合并到 learning-hub
```bash
cd /Volumes/AI_LAB/Github/learning-hub

# 创建子目录
mkdir -p movie-commentary apple tesla-ai

# 复制内容
cp -r /tmp/merge-backup/movie-commentary-learning/* movie-commentary/
cp -r /tmp/merge-backup/apple-learning/* apple/
cp -r /tmp/merge-backup/tesla-ai-learning/* tesla-ai/

# 更新 README
echo "## 合并的学习项目
- [Movie Commentary Learning](./movie-commentary/) - 电影解说学习
- [Apple Learning](./apple/) - Apple 学习
- [Tesla AI Learning](./tesla-ai/) - Tesla AI 学习
" >> README.md

# 提交
git add .
git commit -m "合并学习项目：movie-commentary, apple, tesla-ai"
git push
```

#### 合并到 ai-knowledge-graph
```bash
cd /Volumes/AI_LAB/Github/ai-knowledge-graph

# 创建子目录
mkdir -p security-governance business-automation rag-system workflow-engine

# 复制内容
cp -r /tmp/merge-backup/ai-security-governance/* security-governance/
cp -r /tmp/merge-backup/ai-business-automation/* business-automation/
cp -r /tmp/merge-backup/rag-knowledge-system/* rag-system/
cp -r /tmp/merge-backup/ai-agent-workflow-engine/* workflow-engine/

# 更新 README
echo "## 合并的 AI 项目
- [Security Governance](./security-governance/) - AI 安全治理
- [Business Automation](./business-automation/) - AI 业务自动化
- [RAG System](./rag-system/) - RAG 知识系统
- [Workflow Engine](./workflow-engine/) - AI 工作流引擎
" >> README.md

# 提交
git add .
git commit -m "合并 AI 项目：security, business-automation, rag, workflow"
git push
```

### 阶段 4：删除旧仓库
```bash
# 需要授权
gh repo delete srxly888-creator/movie-commentary-learning --yes
gh repo delete srxly888-creator/apple-learning --yes
gh repo delete srxly888-creator/tesla-ai-learning --yes
gh repo delete srxly888-creator/ai-security-governance --yes
gh repo delete srxly888-creator/ai-business-automation --yes
gh repo delete srxly888-creator/rag-knowledge-system --yes
gh repo delete srxly888-creator/ai-agent-workflow-engine --yes
```

## ⚠️ 风险控制

### 检查清单
- [ ] 确认没有未合并的 PR
- [ ] 确认没有活跃的 issues
- [ ] 确认没有其他用户 fork
- [ ] 备份重要内容

### 执行时机
- 等待 `delete_repo` 授权后执行
- 先合并，后删除

## 📈 预期结果

### 删除后统计
- **删除**: 7 个原创仓库
- **保留**: 28 个原创仓库
- **合并后**: learning-hub 和 ai-knowledge-graph 更丰富

### 最终结构
- **核心项目**: 6 个（有 stars）
- **学习项目**: 12 个（合并后）
- **工具项目**: 5 个
- **私人项目**: 10 个
- **有价值的 Fork**: 3 个

---

**时间**: 2026-03-30 00:10
**状态**: 🟡 计划中，等待授权
