# Git版本控制教程 - 从入门到精通

> **版本**: 2.0 | **工具**: Git | **难度**: ⭐⭐ 入门

---

## 📋 目录

- [Git基础](#git基础)
- [常用命令](#常用命令)
- [分支管理](#分支管理)
- [协作流程](#协作流程)
- [最佳实践](#最佳实践)

---

## 🤔 Git基础

### 什么是Git？
Git是分布式版本控制系统，用于跟踪代码变化。

### 为什么使用Git？
- ✅ 版本回溯
- ✅ 多人协作
- ✅ 代码备份
- ✅ 分支开发
- ✅ 变更对比

### Git vs GitHub
- **Git**: 版本控制工具（本地）
- **GitHub**: 代码托管平台（远程）

---

## 🚀 安装与配置

### 安装Git

#### macOS
```bash
# 使用Homebrew安装
brew install git

# 验证安装
git --version
```

#### Windows
```bash
# 下载安装包
https://git-scm.com/download/win

# 默认安装即可
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt install git

# 验证安装
git --version
```

### 配置Git

#### 用户信息
```bash
# 设置用户名
git config --global user.name "Your Name"

# 设置邮箱
git config --global user.email "your.email@example.com"

# 查看配置
git config --list
```

#### 初始化仓库
```bash
# 创建新目录
mkdir my-project
cd my-project

# 初始化Git仓库
git init

# 创建文件
echo "# My Project" > README.md

# 添加文件
git add README.md

# 提交
git commit -m "Initial commit"
```

---

## 📝 常用命令

### 1. 基本操作

#### 查看状态
```bash
# 查看仓库状态
git status

# 输出示例：
# On branch main
# Changes not staged for commit:
#   modified:   file.py
# Untracked files:
#   new_file.py
```

#### 添加文件
```bash
# 添加单个文件
git add file.py

# 添加所有文件
git add .

# 添加特定类型
git add *.py

# 添加目录
git add src/
```

#### 提交更改
```bash
# 提交并添加消息
git commit -m "Add new feature"

# 提交并添加详细消息
git commit -m "Add user authentication

- Add login function
- Add password validation
- Fix bug in session management"
```

### 2. 查看历史

#### 查看提交历史
```bash
# 查看提交历史
git log

# 查看简洁历史
git log --oneline

# 查看最近5次提交
git log -5

# 查看图表
git log --graph --oneline
```

#### 查看文件变化
```bash
# 查看文件变化
git diff

# 查看暂存区变化
git diff --staged

# 查看特定文件
git diff file.py
```

### 3. 撤销操作

#### 撤销暂存
```bash
# 撤销所有暂存
git reset

# 撤销特定文件暂存
git reset file.py

# 撤销上一次提交（保留更改）
git reset --soft HEAD~1

# 撤销上一次提交（丢弃更改）
git reset --hard HEAD~1
```

#### 恢复文件
```bash
# 恢复到上一次提交
git checkout -- file.py

# 恢复到指定提交
git checkout <commit-hash> -- file.py
```

---

## 🌿 分支管理

### 创建与切换

#### 创建分支
```bash
# 创建新分支
git branch feature-login

# 创建并切换到新分支
git checkout -b feature-login

# 查看所有分支
git branch

# 输出示例：
#   main
# * feature-login  # 当前分支
```

#### 切换分支
```bash
# 切换到已有分支
git checkout main

# 切换到上一个分支
git checkout -
```

### 合并分支

#### 合并分支
```bash
# 切换到main分支
git checkout main

# 合并feature分支
git merge feature-login

# 删除已合并的分支
git branch -d feature-login
```

#### 解决冲突
```python
# 冲突示例
<<<<<<< HEAD
def function():
    return "main version"
=======
def function():
    return "feature version"
>>>>>>> feature-login
```

#### 手动解决
```python
# 修改为正确版本
def function():
    return "correct version"
```

```bash
# 标记为已解决
git add file.py

# 完成合并
git commit -m "Merge feature-login"
```

---

## 🌐 远程仓库

### 连接远程仓库

#### 添加远程仓库
```bash
# 添加远程仓库
git remote add origin https://github.com/username/repo.git

# 查看远程仓库
git remote -v

# 查看远程分支
git branch -r
```

#### 推送代码
```bash
# 推送到远程
git push origin main

# 推送所有分支
git push --all origin

# 推送并设置上游
git push -u origin feature-login
```

#### 拉取代码
```bash
# 拉取远程更新
git pull origin main

# 拉取特定分支
git pull origin feature-login

# 拉取但不合并
git fetch origin
```

### 克隆仓库

#### 克隆现有仓库
```bash
# 克隆仓库
git clone https://github.com/username/repo.git

# 克隆到指定目录
git clone https://github.com/username/repo.git my-project
```

---

## 🔄 协作流程

### Git Flow工作流

#### 分支类型
```
main/master: 生产环境分支
develop: 开发环境分支
feature/*: 功能分支
hotfix/*: 修复分支
release/*: 发布分支
```

#### 开发流程
```bash
# 1. 从develop创建功能分支
git checkout develop
git checkout -b feature/new-feature

# 2. 开发功能
# 编写代码
git add .
git commit -m "Add new feature"

# 3. 推送功能分支
git push -u origin feature/new-feature

# 4. 创建Pull Request/Merge Request
# 在GitHub/GitLab上创建PR

# 5. 合并到develop后删除功能分支
git checkout develop
git pull
git branch -d feature/new-feature
```

### Fork工作流

#### 参与开源项目
```bash
# 1. Fork项目
# 在GitHub上点击Fork按钮

# 2. 克隆Fork的仓库
git clone https://github.com/your-username/repo.git
cd repo

# 3. 添加上游仓库
git remote add upstream https://github.com/original-username/repo.git

# 4. 创建功能分支
git checkout -b feature/my-feature

# 5. 开发并提交
git add .
git commit -m "Add my feature"

# 6. 推送到你的Fork
git push -u origin feature/my-feature

# 7. 创建Pull Request
# 在GitHub上从你的Fork创建PR到原始仓库

# 8. 同步上游更新
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

---

## 🎯 最佳实践

### 提交规范

#### 提交信息格式
```bash
# 格式：<类型>(<范围>): <描述>

# 类型：
# feat: 新功能
# fix: 修复bug
# docs: 文档更新
# style: 代码格式（不影响功能）
# refactor: 重构
# perf: 性能优化
# test: 测试
# chore: 构建/工具

# 示例：
git commit -m "feat(auth): add user login"
git commit -m "fix(api): resolve timeout issue"
git commit -m "docs(readme): update installation guide"
```

#### 提交粒度
```bash
# ✅ 好的提交：一个功能一次提交
git commit -m "Add user registration"

# ❌ 不好的提交：多个功能一次提交
git commit -m "Add login, registration, profile, and settings"
```

### .gitignore配置

#### 忽略文件
```bash
# .gitignore示例

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

# 日志
*.log

# 敏感信息
.env
*.key
config.ini
```

#### 创建.gitignore
```bash
# 创建文件
cat > .gitignore << EOF
__pycache__/
*.py[cod]
*.so
venv/
.DS_Store
EOF

# 提交.gitignore
git add .gitignore
git commit -m "Add .gitignore"
```

---

## 🔧 高级技巧

### 1. Stash暂存

#### 暂存工作
```bash
# 暂存当前工作
git stash

# 暂存并添加消息
git stash save "Work in progress"

# 查看stash列表
git stash list

# 恢复stash
git stash pop

# 恢复指定stash
git stash apply stash@{0}

# 删除stash
git stash drop stash@{0}
```

### 2. Rebase变基

#### 变基操作
```bash
# 变基到main
git checkout feature-branch
git rebase main

# 变基解决冲突后
git rebase --continue

# 放弃变基
git rebase --abort
```

### 3. Cherry-pick精选

#### 精选提交
```bash
# 从其他分支挑选提交
git cherry-pick <commit-hash>

# 精选多个提交
git cherry-pick <hash1> <hash2> <hash3>
```

---

## 📊 检查清单

### 提交前
- [ ] 代码编译通过
- [ ] 通过测试
- [ ] 遵循代码规范
- [ ] 更新文档
- [ ] .gitignore配置正确

### 推送前
- [ ] 拉取最新代码
- [ ] 解决冲突
- [ ] 本地测试通过
- [ ] 提交信息清晰

---

## 📚 扩展阅读

### 官方文档
- Pro Git Book: https://git-scm.com/book/zh/v2
- GitHub文档: https://docs.github.com/

### 工具推荐
- GitKraken: 图形化Git客户端
- SourceTree: 免费Git GUI
- GitHub Desktop: GitHub官方客户端

---

**创建时间**: 2026-03-23 18:35
**版本**: 2.0
**工具**: Git
**状态**: 🔥 火力全开完成

🔥 **Git是程序员的必备技能！** 🔥
