# 🔴 PR不纯粹的深刻教训

> **记录时间**: 2026-03-22 18:15
> **严重程度**: 🔴🔴 **高**
> **影响**: PR被拒绝/关闭，浪费时间，影响可信度

---

## 🚨 问题描述

### **背景**

给 karpathy/autoresearch 提交中文翻译PR，连续犯了3次错误：

**PR #377**:
- ❌ 包含GPU支持修改（commit 916a8de）
- ❌ 包含学习笔记（commit 04f5006）
- ❌ 包含英文学习笔记（commit b0c45f9）
- **结果**: 关闭

**PR #378**:
- ❌ 包含LEARNING-EN.md（学习笔记）
- **结果**: 关闭

**PR #379**:
- ✅ 仅包含README翻译
- **结果**: 正确

---

## 🔍 根本原因分析

### **1. 基于错误的分支**

❌ **错误做法**:
```bash
# 基于自己的master分支
git checkout -b translation-branch master
```

✅ **正确做法**:
```bash
# 基于upstream/master
git fetch upstream
git checkout -b translation-branch upstream/master
```

**原因**: 自己的master包含了之前的commit，会污染PR

---

### **2. 没有检查commit内容**

❌ **错误做法**:
```bash
# 提交后直接推送
git add .
git commit -m "Add translation"
git push
```

✅ **正确做法**:
```bash
# 提交前检查
git add translation-files-only
git commit -m "Add translation"

# 检查commit内容
git show --stat
git show --name-only

# 确认只包含翻译文件后再推送
git push
```

---

### **3. 混合不相关的修改**

❌ **错误理解**:
> "反正都是对项目有益的，一起提交吧"

✅ **正确理解**:
> 每个PR应该只做**一件事**

**翻译PR** = 只包含翻译文件
**功能PR** = 只包含功能代码
**文档PR** = 只包含文档修改

---

## 📋 标准流程（翻译PR）

### **步骤1: 准备工作**

```bash
# 1. 确保有upstream
git remote add upstream https://github.com/original/repo.git

# 2. 获取最新代码
git fetch upstream

# 3. 基于upstream创建分支
git checkout -b translation-branch upstream/master
```

---

### **步骤2: 添加翻译文件**

```bash
# 1. 只添加翻译文件
git add README-ZH-CN.md README-ZH-TW.md

# 2. 不要添加其他文件
# ❌ 不要添加学习笔记
# ❌ 不要添加功能代码
# ❌ 不要添加其他修改
```

---

### **步骤3: 检查commit**

```bash
# 1. 提交
git commit -m "Add Chinese Translation"

# 2. 检查commit内容
git show --stat
git show --name-only

# 3. 确认：
# ✅ 只包含翻译文件
# ✅ 没有其他文件
# ✅ 修改行数合理（翻译通常+几百行）
```

---

### **步骤4: 推送并创建PR**

```bash
# 1. 推送到自己的fork
git push -u origin translation-branch

# 2. 创建PR
gh pr create --repo original/repo \
  --title "Add Chinese Translation" \
  --body "Only translation files, no other changes" \
  --head your-fork:translation-branch \
  --base master
```

---

## ✅ 检查清单

**提交PR前必须检查**:

- [ ] **分支基于upstream/master**
  ```bash
  git log upstream/master..HEAD --oneline
  # 应该只有1-2个commit
  ```

- [ ] **只包含翻译文件**
  ```bash
  git show --name-only
  # 应该只有README-ZH-CN.md等翻译文件
  ```

- [ ] **没有其他修改**
  ```bash
  git diff upstream/master --stat
  # 应该只有+行，没有-行
  ```

- [ ] **commit数量合理**
  ```bash
  git log upstream/master..HEAD --oneline
  # 应该只有1个commit
  ```

- [ ] **commit消息清晰**
  ```bash
  git log -1 --pretty=format:"%s"
  # 应该明确说明是翻译
  ```

---

## 🎯 核心原则

### **1. 一个PR = 一件事**

- ✅ **翻译PR**: 只包含翻译
- ✅ **功能PR**: 只包含功能代码
- ✅ **文档PR**: 只包含文档修改
- ✅ **修复PR**: 只包含bug修复

**不要混合！**

---

### **2. 基于upstream，不基于fork**

❌ **错误**: `git checkout -b branch master`（自己的master）
✅ **正确**: `git checkout -b branch upstream/master`

---

### **3. 检查，检查，再检查**

**提交前检查**:
```bash
# 1. 检查文件
git show --name-only

# 2. 检查commit
git log upstream/master..HEAD --oneline

# 3. 检查diff
git diff upstream/master --stat
```

---

## 📊 对比表

| 做法 | PR #377 | PR #378 | PR #379 |
|------|---------|---------|---------|
| **基于分支** | ❌ master | ❌ master | ✅ upstream/master |
| **包含文件** | ❌ 混合 | ❌ 混合 | ✅ 仅翻译 |
| **Commits** | ❌ 多个 | ❌ 多个 | ✅ 1个 |
| **检查内容** | ❌ 未检查 | ❌ 未检查 | ✅ 已检查 |
| **结果** | ❌ 关闭 | ❌ 关闭 | ✅ 正确 |

---

## 💡 永久性原则

### **PR纯度原则**

**定义**: 一个PR应该只做一件事

**衡量标准**:
1. ✅ 所有修改都服务于同一个目的
2. ✅ 可以用一句话描述PR的目标
3. ✅ 审查者不需要理解多个不相关的修改
4. ✅ 合并后不会引入不相关的代码

---

### **分支管理原则**

**规则**:
1. ✅ 功能分支基于 `upstream/master`
2. ✅ 修复分支基于 `upstream/master`
3. ✅ 翻译分支基于 `upstream/master`
4. ❌ 永远不要基于自己的 `master`

**原因**: 自己的master包含历史commit，会污染PR

---

### **提交前检查原则**

**必须检查**:
1. ✅ `git show --name-only`（查看文件列表）
2. ✅ `git show --stat`（查看修改统计）
3. ✅ `git log upstream/master..HEAD`（查看commit历史）
4. ✅ 确认只包含相关修改

**不检查 = 盲目提交 = 错误PR**

---

## 📝 案例分析

### **案例1: Auto-Research翻译PR**

**错误过程**:
```
第1次 (#377):
  基于master → 包含GPU支持+学习笔记 → 关闭

第2次 (#378):
  基于master → 包含学习笔记 → 关闭

第3次 (#379):
  基于upstream/master → 仅翻译 → 成功
```

**教训**: 每次都要基于upstream/master

---

### **案例2: 假设的GPU支持PR**

**错误做法**:
```bash
# 在翻译分支中添加GPU支持
git checkout translation-branch
# 添加GPU代码
git add gpu-support.py
git commit -m "Add GPU support"
git push
```

**正确做法**:
```bash
# GPU支持应该是单独的PR
git checkout -b gpu-support upstream/master
git add gpu-support.py
git commit -m "Add GPU support"
git push
# 创建单独的PR
```

---

## 🔧 工具和脚本

### **PR纯度检查脚本**

```bash
#!/bin/bash
# check-pr-purity.sh

echo "=== PR纯度检查 ==="

# 1. 检查是否基于upstream/master
BASE=$(git merge-base upstream/master HEAD)
if [ "$BASE" != "$(git rev-parse upstream/master)" ]; then
  echo "❌ 警告：分支不是基于upstream/master"
  echo "   当前基于: $BASE"
  echo "   upstream/master: $(git rev-parse upstream/master)"
else
  echo "✅ 基于upstream/master"
fi

# 2. 检查commit数量
COMMITS=$(git log upstream/master..HEAD --oneline | wc -l)
if [ "$COMMITS" -gt 3 ]; then
  echo "❌ 警告：commit数量过多（$COMMITS个）"
  echo "   建议：每个PR不超过3个commit"
else
  echo "✅ commit数量合理（$COMMITS个）"
fi

# 3. 检查修改文件
FILES=$(git diff upstream/master --name-only)
echo ""
echo "修改的文件:"
echo "$FILES"

# 4. 检查文件类型
TRANSLATION=$(echo "$FILES" | grep -E "README.*ZH|README.*CN|README.*TW")
OTHER=$(echo "$FILES" | grep -vE "README.*ZH|README.*CN|README.*TW")

if [ -n "$OTHER" ]; then
  echo ""
  echo "❌ 警告：包含非翻译文件"
  echo "非翻译文件:"
  echo "$OTHER"
else
  echo ""
  echo "✅ 仅包含翻译文件"
fi

# 5. 检查修改行数
ADDITIONS=$(git diff upstream/master --shortstat | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+')
DELETIONS=$(git diff upstream/master --shortstat | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+')

echo ""
echo "修改统计:"
echo "  +$ADDITIONS 行"
echo "  -$DELETIONS 行"

if [ "$DELETIONS" -gt 10 ]; then
  echo "❌ 警告：删除行数过多（$DELETIONS行）"
  echo "   翻译PR通常只有添加，没有删除"
fi

echo ""
echo "=== 检查完成 ==="
```

---

## 📚 参考资料

**Git最佳实践**:
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [How to Write the Perfect Pull Request](https://github.blog/2015-01-21-how-to-write-the-perfect-pull-request/)

**相关教训**:
- Auto-Research PR #377, #378, #379
- 时间: 2026-03-22

---

## 🎯 记住这句话

> **"一个PR = 一件事 = 一句话能说清楚"**

**如果需要多句话描述PR，说明PR不够纯粹。**

---

## 📝 承诺

**以后提交PR时**:
1. ✅ 必须基于 `upstream/master`
2. ✅ 必须检查commit内容
3. ✅ 必须运行检查脚本
4. ✅ 必须确认只包含相关修改
5. ✅ 必须用一句话描述PR目标

**不遵守 = 重复错误 = 浪费时间**

---

**记录时间**: 2026-03-22 18:15
**记录人**: AI Agent
**严重性**: 🔴 高
**教训**: 永不再犯

---

**大佬，教训已永久记录！不会再犯同样的错误！** 🙏
