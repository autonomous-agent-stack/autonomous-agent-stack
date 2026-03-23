# Git版本控制教程 - 从入门到精通

> **版本**: 2.0 | **难度**: ⭐⭐⭐ 进阶 | **重要性**: ⭐⭐⭐ 必读

---

## 📋 Git简介

### 什么是Git？
Git是一个分布式版本控制系统，用于跟踪文件变化。

### 为什么需要Git？
- ✅ **版本管理** - 记录每次修改
- ✅ **回滚能力** - 可以回到任意版本
- ✅ **多人协作** - 团队合作必备
- ✅ **代码备份** - 本地和云端备份

---

## 🚀 Git安装

### macOS
```bash
# 使用Homebrew安装
brew install git

# 验证安装
git --version
```

### Windows
```bash
# 下载安装
https://git-scm.com/download/win

# 或使用winget
winget install --id Git.Git
```

### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install git

# 验证安装
git --version
```

---

## ⚙️ Git配置

### 1. 用户信息
```bash
# 设置用户名
git config --global user.name "你的名字"

# 设置邮箱
git config --global user.email "your.email@example.com"

# 查看配置
git config --list
```

### 2. 初始设置
```bash
# 设置默认分支名称为main
git config --global init.defaultBranch main

# 设置编辑器（VS Code）
git config --global core.editor "code --wait"

# 设置换行符（Windows）
git config --global core.autocrlf true
```

---

## 📁 创建仓库

### 1. 初始化新仓库
```bash
# 创建项目目录
mkdir my-project
cd my-project

# 初始化Git仓库
git init

# 查看状态
git status
```

### 2. 克隆远程仓库
```bash
# 克隆仓库
git clone https://github.com/username/repo.git

# 克隆到指定目录
git clone https://github.com/username/repo.git my-repo
```

---

## 📝 基本操作

### 1. 查看状态
```bash
# 查看当前状态
git status

# 查看简化状态
git status -s
```

### 2. 添加文件
```bash
# 添加所有文件
git add .

# 添加指定文件
git add file.py

# 添加指定类型
git add *.py

# 添加交互式
git add -i
```

### 3. 提交更改
```bash
# 提交更改
git commit -m "提交信息"

# 添加并提交
git commit -am "提交信息"

# 添加详细信息
git commit -m "修复bug" -m "详细说明"
```

### 4. 查看提交历史
```bash
# 查看提交历史
git log

# 查看简化历史
git log --oneline

# 查看图形化历史
git log --graph --oneline
```

---

## 🌿 分支管理

### 1. 创建分支
```bash
# 创建新分支
git branch feature-login

# 创建并切换分支
git checkout -b feature-login
```

### 2. 切换分支
```bash
# 切换到指定分支
git checkout feature-login

# 切换到上一分支
git checkout -
```

### 3. 查看分支
```bash
# 查看所有分支
git branch

# 查看远程分支
git branch -r

# 查看所有分支（包括远程）
git branch -a
```

### 4. 合并分支
```bash
# 合并指定分支到当前分支
git merge feature-login

# 合并但不提交
git merge --no-commit feature-login

# 合并后丢弃分支
git merge --squash feature-login
```

### 5. 删除分支
```bash
# 删除本地分支
git branch -d feature-login

# 强制删除未合并分支
git branch -D feature-login

# 删除远程分支
git push origin --delete feature-login
```

---

## 🔄 远程操作

### 1. 添加远程仓库
```bash
# 添加远程仓库
git remote add origin https://github.com/username/repo.git

# 查看远程仓库
git remote -v
```

### 2. 推送到远程
```bash
# 推送到远程仓库
git push origin main

# 推送所有分支
git push --all origin

# 推送并设置上游
git push -u origin main
```

### 3. 从远程拉取
```bash
# 拉取远程更新
git pull origin main

# 拉取但不合并
git fetch origin

# 拉取指定分支
git pull origin feature-login
```

---

## 🔀 常用场景

### 场景1: 修改错误，需要撤销

```bash
# 撤销工作区修改
git checkout -- file.py

# 撤销暂存区修改
git reset HEAD file.py

# 撤销最近一次提交（保留修改）
git reset --soft HEAD~1

# 撤销最近一次提交（丢弃修改）
git reset --hard HEAD~1
```

### 场景2: 创建功能分支并合并

```bash
# 1. 切换到main分支
git checkout main

# 2. 拉取最新代码
git pull origin main

# 3. 创建功能分支
git checkout -b feature-login

# 4. 开发功能
# ... 编辑代码 ...

# 5. 提交更改
git add .
git commit -m "添加登录功能"

# 6. 推送功能分支
git push -u origin feature-login

# 7. 在GitHub上创建Pull Request

# 8. 合并后删除分支
git checkout main
git pull origin main
git branch -d feature-login
git push origin --delete feature-login
```

### 场景3: 解决合并冲突

```bash
# 1. 尝试合并
git merge feature-login

# 2. 如果有冲突，打开文件
# 标记冲突的文件：
# <<<<<<< HEAD
# 当前分支的内容
# =======
# 合并分支的内容
# >>>>>>> feature-login

# 3. 手动解决冲突
# 编辑文件，选择保留的内容

# 4. 标记为已解决
git add file.py

# 5. 完成合并
git commit -m "解决合并冲突"
```

---

## 🎯 最佳实践

### 1. 提交信息规范

#### 格式：类型(范围): 描述
```bash
# feat: 新功能
git commit -m "feat(用户): 添加登录功能"

# fix: 修复bug
git commit -m "fix(数据库): 修复连接泄漏问题"

# docs: 文档更新
git commit -m "docs(README): 更新安装说明"

# style: 格式调整
git commit -m "style(代码): 统一缩进"

# refactor: 重构
git commit -m "refactor(模块): 简化函数逻辑"

# test: 测试
git commit -m "test(单元测试): 添加登录测试"
```

#### 详细示例
```bash
# 简短描述（50字以内）
git commit -m "fix: 修复登录bug"

# 详细说明
git commit -m "fix: 修复登录验证错误

- 修复用户名包含特殊字符时的验证错误
- 添加输入过滤
- 更新测试用例

Fixes #123"
```

---

### 2. .gitignore文件

#### 忽略不需要的文件
```bash
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# 虚拟环境
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 操作系统
.DS_Store
Thumbs.db

# 敏感信息
*.env
config.ini
secrets.json
```

---

### 3. 分支策略

#### Git Flow（推荐）
```
main（生产环境）
  ↓
develop（开发环境）
  ↓
feature/*（功能分支）
hotfix/*（修复分支）
release/*（发布分支）
```

---

## 🔧 高级操作

### 1. 暂存和恢复

```bash
# 暂存当前工作
git stash

# 查看暂存列表
git stash list

# 恢复暂存
git stash pop

# 恢复但不删除暂存
git stash apply

# 删除暂存
git stash drop
```

### 2. 标签管理

```bash
# 创建标签
git tag v1.0.0

# 创建带注释的标签
git tag -a v1.0.0 -m "版本1.0.0"

# 推送标签
git push origin v1.0.0

# 推送所有标签
git push origin --tags

# 删除标签
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

### 3. 变基（Rebase）

```bash
# 变基到main
git rebase main

# 交互式变基
git rebase -i HEAD~3
```

---

## 📚 常用命令速查

### 日常操作
```bash
git init                  # 初始化仓库
git clone <url>          # 克隆仓库
git status               # 查看状态
git add .               # 添加所有文件
git commit -m "msg"       # 提交
git push origin main      # 推送
git pull origin main      # 拉取
```

### 分支操作
```bash
git branch                # 查看分支
git branch <name>        # 创建分支
git checkout <name>      # 切换分支
git merge <branch>        # 合并分支
git branch -d <name>     # 删除分支
```

### 查看操作
```bash
git log                  # 查看历史
git diff                 # 查看差异
git show <commit>        # 查看提交
git blame <file>         # 查看修改者
```

### 撤销操作
```bash
git checkout -- <file>   # 撤销文件修改
git reset HEAD           # 撤销暂存
git reset --hard HEAD     # 撤销提交
git revert <commit>      # 反转提交
```

---

## 🎓 学习资源

### 官方文档
- Git官方文档: https://git-scm.com/doc
- Git Pro Book: https://git-scm.com/book/zh/v2

### 在线教程
- Learn Git Branching: https://learngitbranching.js.org/
- Git入门指南: https://www.ruanyifeng.com/blog/2015/12/09/git-learning-notes/

### 可视化工具
- GitHub Desktop
- GitKraken
- Sourcetree

---

**创建时间**: 2026-03-23 19:00
**版本**: 2.0
**难度**: ⭐⭐⭐ 进阶
**重要性**: ⭐⭐⭐ 必读

🔥 **Git是程序员的必备技能！** 🔥
