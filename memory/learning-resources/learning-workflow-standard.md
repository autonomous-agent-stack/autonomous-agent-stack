# 🔬 开源项目学习工作流程（标准化）

> **版本**: 1.0
> **时间**: 2026-03-22 18:25
> **基于**: Auto-Research PR 教训 + 上游一致性探索

---

## 📋 目录

1. [核心原则](#核心原则)
2. [工作流程](#工作流程)
3. [学习笔记模板](#学习笔记模板)
4. [PR 规则](#pr-规则)
5. [定期维护](#定期维护)
6. [工具和脚本](#工具和脚本)

---

## 🎯 核心原则

### **1. 一个项目 = 一个 Fork**
- ✅ Fork 到 `srxly888-creator/<project-name>`
- ✅ 在 Fork 中学习和做笔记
- ✅ 定期与 upstream 同步

### **2. 学习笔记留在 Fork**
- ✅ 创建 `.learning/` 目录
- ✅ 学习笔记不 PR 到上游
- ✅ 个人理解，留在自己的 fork

### **3. 翻译可以 PR**
- ✅ 翻译帮助所有用户
- ✅ 可以 PR 到上游
- ✅ 但要确保 PR 纯净（仅翻译）

### **4. 代码修改单独 PR**
- ✅ Bug 修复、功能增强单独 PR
- ✅ 不与翻译混合
- ✅ 基于 `upstream/master`

---

## 🔄 工作流程

### **Phase 1: 学习前准备（5分钟）**

#### **步骤 1: 检查上游结构**
```bash
# 检查上游文件结构
curl -s "https://api.github.com/repos/<owner>/<repo>/contents/" | jq -r '.[].name'

# 检查是否有文档目录
curl -s "https://api.github.com/repos/<owner>/<repo>/contents/" | jq -r '.[].name' | grep -i "doc\|learn\|guide"
```

**记录下来**:
- 上游有哪些核心文件？
- 上游是否有文档目录？
- 上游的风格是什么？

#### **步骤 2: Fork 项目**
```bash
# 1. 在 GitHub 上 Fork
# 2. Clone 到本地
cd ~/.openclaw/workspace
git clone https://github.com/srxly888-creator/<project-name>.git
cd <project-name>

# 3. 添加 upstream
git remote add upstream https://github.com/<owner>/<repo>.git

# 4. 检查远程配置
git remote -v
```

#### **步骤 3: 创建学习笔记目录**
```bash
# 创建 .learning 目录
mkdir -p .learning

# 创建索引文件
cat > .learning/README.md << 'EOF'
# <Project Name> 学习笔记

> **项目**: <owner>/<repo> (<stars> Stars)
> **学习时间**: YYYY-MM-DD
> **学习目的**: <目的>

---

## 📚 学习笔记

### **中文笔记**
1. [核心概念](./00-核心概念.md) - <描述>
2. [快速开始](./01-快速开始.md) - <描述>
3. [实验记录](./02-实验记录.md) - <描述>

### **English Notes**
1. [Core Concepts](./00-Core-Concepts.md) - <description>
2. [Quick Start](./01-Quick-Start.md) - <description>
3. [Experiments](./02-Experiments.md) - <description>

---

## 🔗 快速链接

- **上游仓库**: https://github.com/<owner>/<repo>
- **我的 Fork**: https://github.com/srxly888-creator/<project-name>
- **学习中心**: https://github.com/srxly888-creator/ai-agent-learning-hub

---

**注意**: 这些学习笔记不会 PR 到上游仓库。它们仅用于个人学习。
EOF

# 创建第一个学习笔记
cat > .learning/00-核心概念.md << 'EOF'
# 核心概念

## 什么是 <Project Name>？

<描述>

## 核心特性

1. <特性1>
2. <特性2>
3. <特性3>

## 应用场景

- <场景1>
- <场景2>
- <场景3>

---

**学习时间**: YYYY-MM-DD
EOF

# 提交到 fork
git add .learning/
git commit -m "📚 初始化学习笔记目录"
git push origin master
```

---

### **Phase 2: 深度学习（30-60分钟）**

#### **步骤 1: 阅读核心文件**
```bash
# 1. 阅读 README.md
cat README.md

# 2. 阅读核心代码
# （根据项目不同，选择不同的文件）

# 3. 阅读文档
# （如果有 docs/ 目录）
```

#### **步骤 2: 记录学习笔记**
```bash
# 在 .learning/ 目录中创建笔记

# 示例 1: 核心概念
cat > .learning/00-核心概念.md << 'EOF'
# 核心概念

## 什么是 <Project>？

<用自己的话解释>

## 核心架构

\`\`\`
<架构图或代码片段>
\`\`\`

## 关键技术

1. **技术1**: <解释>
2. **技术2**: <解释>
3. **技术3**: <解释>

## 我的理解

<个人思考>

## 疑问

- [ ] 疑问1
- [ ] 疑问2
EOF

# 示例 2: 快速开始
cat > .learning/01-快速开始.md << 'EOF'
# 快速开始

## 环境要求

- Python 3.10+
- GPU: <要求>

## 安装步骤

\`\`\`bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行
python main.py
\`\`\`

## 遇到的问题

1. **问题1**: <描述> → 解决: <方法>
2. **问题2**: <描述> → 解决: <方法>

## 验证成功

✅ <验证方法>
EOF

# 提交学习笔记
git add .learning/
git commit -m "📚 添加学习笔记：<主题>"
git push origin master
```

#### **步骤 3: 实践验证**
```bash
# 1. 运行代码
python main.py

# 2. 修改参数，观察结果
# 3. 记录实验结果

# 示例: 记录实验
cat > .learning/02-实验记录.md << 'EOF'
# 实验记录

## 实验 1: <标题>

**时间**: YYYY-MM-DD HH:MM
**目的**: <目的>

### 配置

\`\`\`python
# 配置参数
learning_rate = 0.001
batch_size = 32
\`\`\`

### 结果

- ✅ 成功/失败
- 性能: <数据>
- 观察: <观察>

### 结论

<结论>

---

## 实验 2: <标题>

...
EOF

git add .learning/
git commit -m "🔬 添加实验记录：<实验名称>"
git push origin master
```

---

### **Phase 3: 贡献回社区（可选）**

#### **场景 1: 翻译（推荐）**

```bash
# 1. 基于 upstream/master 创建翻译分支
git fetch upstream
git checkout -b chinese-translation upstream/master

# 2. 创建翻译文件
cat > README-ZH-CN.md << 'EOF'
# <Project Name>

<翻译 README.md>

**翻译原则**:
- ✅ 保留代码块不翻译
- ✅ 保留链接不翻译
- ✅ 技术术语保持英文
EOF

# 3. 检查 commit
bash ~/.openclaw/scripts/check-pr-purity.sh

# 4. 推送
git push -u origin chinese-translation

# 5. 创建 PR
gh pr create --repo <owner>/<repo> \
  --title "🌍 Add Chinese Translation (Simplified)" \
  --body "Only translation, no other changes."
```

#### **场景 2: Bug 修复**

```bash
# 1. 基于 upstream/master 创建修复分支
git fetch upstream
git checkout -b fix-<bug-name> upstream/master

# 2. 修复代码
# ...

# 3. 测试
# ...

# 4. 提交
git add <files>
git commit -m "🐛 Fix: <描述>"

# 5. 检查 commit
bash ~/.openclaw/scripts/check-pr-purity.sh

# 6. 推送并创建 PR
git push -u origin fix-<bug-name>
gh pr create --repo <owner>/<repo>
```

---

## 📚 学习笔记模板

### **模板 1: 核心概念**
```markdown
# 核心概念

## 什么是 <Project>？

<用自己的话解释，不超过 3 句话>

## 核心架构

<架构图或代码片段>

## 关键技术

1. **技术1**: <解释>
2. **技术2**: <解释>
3. **技术3**: <解释>

## 应用场景

- <场景1>
- <场景2>
- <场景3>

## 与其他项目的关系

- 项目A → 关系1
- 项目B → 关系2

## 我的理解

<个人思考，3-5 点>

## 疑问

- [ ] 疑问1
- [ ] 疑问2
- [ ] 疑问3

---

**学习时间**: YYYY-MM-DD
**学习时长**: XX 分钟
```

### **模板 2: 快速开始**
```markdown
# 快速开始

## 环境要求

- 操作系统: <要求>
- Python: <版本>
- GPU: <要求>
- 其他: <要求>

## 安装步骤

\`\`\`bash
# 1. 安装依赖
<命令>

# 2. 配置
<命令>

# 3. 运行
<命令>
\`\`\`

## 验证成功

✅ <验证方法>

## 遇到的问题

### 问题 1: <描述>

**错误信息**:
\`\`\`
<错误>
\`\`\`

**解决方法**:
\`\`\`
<解决>
\`\`\`

---

**安装时间**: YYYY-MM-DD
**安装时长**: XX 分钟
```

### **模板 3: 实验记录**
```markdown
# 实验记录

## 实验 1: <标题>

**时间**: YYYY-MM-DD HH:MM
**目的**: <目的>
**预期**: <预期结果>

### 配置

\`\`\`python
# 配置参数
param1 = value1
param2 = value2
\`\`\`

### 执行

\`\`\`bash
<命令>
\`\`\`

### 结果

- 状态: ✅ 成功 / ❌ 失败
- 性能: <数据>
- 输出: <关键输出>

### 观察

<观察到的现象>

### 结论

<结论>

### 下一步

- [ ] <下一步1>
- [ ] <下一步2>

---

**实验时长**: XX 分钟
```

---

## 🎯 PR 规则

### **什么可以 PR？**

| 内容 | 是否可以 PR | 理由 |
|------|-----------|------|
| **翻译**（README-ZH-CN.md）| ✅ 是 | 帮助所有用户 |
| **Bug 修复**| ✅ 是 | 改善项目 |
| **功能增强**| ✅ 是 | 增加价值 |
| **文档改进**| ✅ 是 | 帮助用户 |
| **学习笔记**| ❌ 否 | 个人理解 |
| **实验记录**| ❌ 否 | 个人学习 |
| **个人配置**| ❌ 否 | 仅自己使用 |

### **PR 检查清单**

提交 PR 前必须检查：

- [ ] **基于 upstream/master**
  ```bash
  git fetch upstream
  git checkout -b <branch-name> upstream/master
  ```

- [ ] **只包含相关修改**
  ```bash
  git show --name-only
  # 应该只有相关文件
  ```

- [ ] **运行检查脚本**
  ```bash
  bash ~/.openclaw/scripts/check-pr-purity.sh
  ```

- [ ] **commit 数量合理**
  ```bash
  git log upstream/master..HEAD --oneline
  # 应该 ≤3 个 commit
  ```

- [ ] **可以用一句话描述**
  - ✅ "添加中文翻译"
  - ✅ "修复 XX bug"
  - ❌ "添加翻译 + 修复 bug + 学习笔记"

---

## 🔧 定期维护

### **每周同步 upstream**

```bash
# 1. 获取最新代码
git fetch upstream

# 2. 切换到 master
git checkout master

# 3. 合并更新
git merge upstream/master

# 4. 解决冲突（如有）
# ...

# 5. 推送
git push origin master

# 6. 更新学习笔记（如有必要）
# ...

# 7. 提交更新
git add .learning/
git commit -m "📚 更新学习笔记（同步 upstream <version>）"
git push origin master
```

### **每月整理学习笔记**

```bash
# 1. 检查学习笔记完整性
ls -la .learning/

# 2. 更新索引
# 添加新的学习笔记到 .learning/README.md

# 3. 清理过时内容
# 删除或标记过时的笔记

# 4. 提交整理
git add .learning/
git commit -m "📚 整理学习笔记"
git push origin master
```

---

## 🛠️ 工具和脚本

### **自动创建学习笔记目录**

```bash
#!/bin/bash
# create-learning-dir.sh

PROJECT_NAME=$1
OWNER=$2
REPO=$3

if [ -z "$PROJECT_NAME" ] || [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  echo "用法: bash create-learning-dir.sh <project-name> <owner> <repo>"
  echo "示例: bash create-learning-dir.sh autoresearch karpathy autoresearch"
  exit 1
fi

# 创建 .learning 目录
mkdir -p .learning

# 创建 README.md
cat > .learning/README.md << EOF
# $PROJECT_NAME 学习笔记

> **项目**: $OWNER/$REPO
> **学习时间**: $(date +%Y-%m-%d)
> **学习目的**: <目的>

---

## 📚 学习笔记

### **中文笔记**
1. [核心概念](./00-核心概念.md) - 什么是 $PROJECT_NAME？
2. [快速开始](./01-快速开始.md) - 安装和运行
3. [实验记录](./02-实验记录.md) - 实验日志

---

## 🔗 快速链接

- **上游仓库**: https://github.com/$OWNER/$REPO
- **我的 Fork**: https://github.com/srxly888-creator/$PROJECT_NAME
- **学习中心**: https://github.com/srxly888-creator/ai-agent-learning-hub

---

**注意**: 这些学习笔记不会 PR 到上游仓库。它们仅用于个人学习。
EOF

# 创建核心概念笔记
cat > .learning/00-核心概念.md << 'EOF'
# 核心概念

## 什么是 <Project Name>？

<用自己的话解释>

## 核心架构

<架构图或代码片段>

## 关键技术

1. **技术1**: <解释>
2. **技术2**: <解释>

## 我的理解

<个人思考>

---

**学习时间**: $(date +%Y-%m-%d)
EOF

echo "✅ 已创建 .learning/ 目录"
echo ""
echo "下一步:"
echo "1. 阅读 README.md 和核心代码"
echo "2. 填写 .learning/00-核心概念.md"
echo "3. 创建更多学习笔记"
echo "4. 定期与 upstream 同步"
```

**使用方法**:
```bash
# 保存脚本
chmod +x ~/.openclaw/scripts/create-learning-dir.sh

# 使用
cd ~/.openclaw/workspace/new-project
bash ~/.openclaw/scripts/create-learning-dir.sh new-project owner repo
```

---

## 📊 示例：学习 Auto-Research

### **Phase 1: 准备**
```bash
# 1. Fork
cd ~/.openclaw/workspace
git clone https://github.com/srxly888-creator/autoresearch.git
cd autoresearch
git remote add upstream https://github.com/karpathy/autoresearch.git

# 2. 检查上游
curl -s "https://api.github.com/repos/karpathy/autoresearch/contents/" | jq -r '.[].name'
# 输出: README.md, prepare.py, train.py, program.md, etc.

# 3. 创建学习笔记目录
bash ~/.openclaw/scripts/create-learning-dir.sh autoresearch karpathy autoresearch
```

### **Phase 2: 学习**
```bash
# 1. 阅读 README.md
cat README.md

# 2. 填写核心概念
vim .learning/00-核心概念.md
# 写入: 什么是 autoresearch？核心架构是什么？

# 3. 尝试运行
uv run prepare.py
uv run train.py

# 4. 记录实验
vim .learning/02-实验记录.md
# 记录: 配置、结果、观察

# 5. 提交学习笔记
git add .learning/
git commit -m "📚 添加学习笔记：核心概念和实验"
git push origin master
```

### **Phase 3: 贡献**
```bash
# 1. 创建翻译分支
git fetch upstream
git checkout -b chinese-translation upstream/master

# 2. 创建翻译
cat > README-ZH-CN.md << 'EOF'
# autoresearch

<翻译 README.md>
EOF

# 3. 检查
bash ~/.openclaw/scripts/check-pr-purity.sh

# 4. 推送并创建 PR
git push -u origin chinese-translation
gh pr create --repo karpathy/autoresearch
```

---

## ✅ 总结

### **学习流程（简化版）**

1. **Fork → Clone → 添加 upstream**
2. **创建 `.learning/` 目录**
3. **学习 → 记录笔记 → 实践验证**
4. **定期同步 upstream**
5. **可选：翻译 PR / Bug 修复 PR**

### **核心原则（记住这 4 条）**

1. ✅ **学习笔记留在 fork**（不 PR）
2. ✅ **翻译可以 PR**（帮助他人）
3. ✅ **基于 upstream/master**（保持纯净）
4. ✅ **一个 PR = 一件事**（不混合）

### **工具支持**

- ✅ PR 纯度检查脚本: `~/.openclaw/scripts/check-pr-purity.sh`
- ✅ 学习笔记目录创建脚本: `~/.openclaw/scripts/create-learning-dir.sh`
- ✅ 详细文档: `memory/pr-purity-lesson.md`
- ✅ 上游一致性探索: `memory/learning-notes-upstream-sync.md`

---

**大佬，这是标准化的学习工作流程！以后按照这个流程来就不会出错！** 🚀
