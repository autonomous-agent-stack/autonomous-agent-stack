# 分支整合计划 - 2026-03-26

## 🎯 目标
修复"不能联系上文"问题，建立统一稳定的智能底座。

## 📊 当前分支状态

### ✅ 已合并到 main（17 个提交）
```
7f80373 feat(knowledge-graph): 玛露轻量级知识图谱与 Micro-GraphRAG 集成
4c16627 Merge branch 'codex/continue-autonomous-agent-stack' into main
20eb393 Merge branch 'feature/omni-assistant-integration' into main
d72d7d2 Merge branch 'codex/p3-openviking-mirofish-integration' into main
7e6606d feat(security): 玛露群组安全集成完成 - Phase 2-4
```

### ⏳ 待合并分支（13 个）

#### 🔴 高优先级（核心功能）
1. **feature/p4-vision-integration**
   - 状态：✅ 测试通过
   - 功能：多模态视觉接入 + P4 演化闭环
   - 提交：680cdbb
   - 风险：有合并冲突

2. **feature/opensage-integration**
   - 状态：✅ 测试通过
   - 功能：OpenSage 架构集成 + Gatekeeper
   - 提交：bcb601e
   - 风险：有合并冲突

3. **codex/urgent-api-sse-validation**
   - 状态：⚠️ 本地存在，远程不存在
   - 功能：API SSE 验证
   - 风险：需要检查

#### 🟡 中优先级（增强功能）
4. **feature/4-agent-matrix-bridge**
   - 功能：Agent 矩阵桥接
   - 状态：已提交未推送

5. **codex/vscode-direct-runtime-orchestration**
   - 功能：VSCode 直接运行时编排

6. **codex/prompt-orchestration-masfactory**
   - 功能：Prompt 编排 + MASFactory 集成

#### 🟢 低优先级（实验性）
7. **codex/opensage-decomposer-single-file**
8. **codex/knowledge-fusion-share-method**
9. **feature/cluster-management**
10. **fix/context-awareness**
11. **fix/image-handling**
12. **p4-super-agent-stack**
13. **codex/continue-autonomous-agent-stack**

---

## 🔧 整合方案

### 方案 A：逐个合并（推荐）
```bash
# 1. 创建整合分支
git checkout -b integration/2026-03-26-consolidation

# 2. 逐个合并关键分支
git merge feature/p4-vision-integration --no-ff
# 解决冲突
git commit

git merge feature/opensage-integration --no-ff
# 解决冲突
git commit

# 3. 测试
python3 tests/test_p4_vision.py

# 4. 合并到 main
git checkout main
git merge integration/2026-03-26-consolidation --no-ff
git push origin main
```

### 方案 B：Cherry-pick（精确控制）
```bash
# 只提取关键提交
git cherry-pick 680cdbb  # P4 Vision
git cherry-pick bcb601e  # OpenSage
```

### 方案 C：重建（最干净）
```bash
# 从 main 创建新分支
git checkout -b feature/consolidated-base main

# 重新实现核心功能
# 丢弃所有实验性分支
```

---

## 🚨 冲突解决策略

### 已知冲突文件
1. `src/autoresearch/api/dependencies.py`
2. `src/autoresearch/api/main.py`
3. `src/autoresearch/api/routers/openclaw.py`

### 解决原则
- **保留最新版本**：优先保留 main 的修改
- **合并功能**：保留两个分支的新增功能
- **删除冗余**：移除重复代码

---

## 📋 执行清单

### Phase 1：准备工作
- [x] 推送 main 分支（17 个提交）
- [x] 清理工作区
- [ ] 创建整合分支

### Phase 2：合并关键分支
- [ ] 合并 feature/p4-vision-integration
- [ ] 解决冲突
- [ ] 合并 feature/opensage-integration
- [ ] 解决冲突

### Phase 3：测试验证
- [ ] 运行所有测试
- [ ] 修复失败的测试
- [ ] 代码审查

### Phase 4：推送到 main
- [ ] 合并到 main
- [ ] 推送到远程
- [ ] 清理已合并的分支

---

## 📌 下一步行动

**立即执行**：
1. 创建整合分支 `integration/2026-03-26-consolidation`
2. 合并 `feature/p4-vision-integration`
3. 解决冲突并测试
4. 推送到 main

**时间估算**：30 分钟

---

**创建时间**：2026-03-26 09:10 GMT+8
