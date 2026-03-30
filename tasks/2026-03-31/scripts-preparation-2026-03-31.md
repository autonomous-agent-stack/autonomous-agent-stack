# GitHub 清理脚本准备（2026-03-31 00:05）

## 🎯 目标
准备授权后立即执行的清理脚本

## 📜 脚本 1：批量删除 Fork（63 个）

### delete-forks.sh
```bash
#!/bin/bash
# 批量删除 0 stars 的 Fork 仓库
# 使用方法: ./delete-forks.sh

set -e

FORKS_FILE="/tmp/forks_to_delete.txt"
LOG_FILE="/tmp/fork-delete-log-$(date +%Y%m%d-%H%M%S).log"

echo "开始删除 Fork 仓库..." | tee -a "$LOG_FILE"
echo "日志文件: $LOG_FILE" | tee -a "$LOG_FILE"

# 检查文件是否存在
if [ ! -f "$FORKS_FILE" ]; then
  echo "错误: 找不到 $FORKS_FILE" | tee -a "$LOG_FILE"
  exit 1
fi

# 统计
TOTAL=$(wc -l < "$FORKS_FILE")
echo "待删除仓库: $TOTAL 个" | tee -a "$LOG_FILE"

# 删除
SUCCESS=0
FAILED=0

while read -r repo; do
  if [ -z "$repo" ]; then
    continue
  fi

  echo "删除 $repo..." | tee -a "$LOG_FILE"

  if gh repo delete "srxly888-creator/$repo" --yes 2>&1 | tee -a "$LOG_FILE"; then
    echo "✅ 成功删除: $repo" | tee -a "$LOG_FILE"
    ((SUCCESS++))
  else
    echo "❌ 删除失败: $repo" | tee -a "$LOG_FILE"
    ((FAILED++))
  fi

  # 避免速率限制
  sleep 1
done < "$FORKS_FILE"

# 总结
echo "================================" | tee -a "$LOG_FILE"
echo "删除完成!" | tee -a "$LOG_FILE"
echo "成功: $SUCCESS" | tee -a "$LOG_FILE"
echo "失败: $FAILED" | tee -a "$LOG_FILE"
echo "总计: $TOTAL" | tee -a "$LOG_FILE"
```

## 📜 脚本 2：合并原创仓库（7 个）

### merge-repos.sh
```bash
#!/bin/bash
# 合并 7 个原创仓库到 learning-hub 和 ai-knowledge-graph
# 使用方法: ./merge-repos.sh

set -e

BACKUP_DIR="/tmp/merge-backup"
LOG_FILE="/tmp/merge-repos-log-$(date +%Y%m%d-%H%M%S).log"

echo "开始合并仓库..." | tee -a "$LOG_FILE"
echo "日志文件: $LOG_FILE" | tee -a "$LOG_FILE"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# ========== 合并到 learning-hub ==========
echo "=== 合并到 learning-hub ===" | tee -a "$LOG_FILE"

REPOS="movie-commentary-learning apple-learning tesla-ai-learning"

for repo in $REPOS; do
  echo "克隆 $repo..." | tee -a "$LOG_FILE"

  if gh repo clone "srxly888-creator/$repo" "$BACKUP_DIR/$repo" 2>&1 | tee -a "$LOG_FILE"; then
    echo "✅ 克隆成功: $repo" | tee -a "$LOG_FILE"
  else
    echo "❌ 克隆失败: $repo" | tee -a "$LOG_FILE"
    continue
  fi
done

# 创建子目录并复制
cd /Volumes/AI_LAB/Github/learning-hub

for repo in $REPOS; do
  subdir=$(echo "$repo" | sed 's/-learning//')
  echo "创建子目录: $subdir" | tee -a "$LOG_FILE"

  mkdir -p "$subdir"
  cp -r "$BACKUP_DIR/$repo"/* "$subdir/" 2>&1 | tee -a "$LOG_FILE"
done

# 更新 README
cat >> README.md << 'EOF'

## 合并的学习项目
- [Movie Commentary](./movie-commentary/) - 电影解说学习
- [Apple Learning](./apple/) - Apple 学习
- [Tesla AI Learning](./tesla-ai/) - Tesla AI 学习
EOF

# 提交
git add .
git commit -m "合并学习项目：movie-commentary, apple, tesla-ai"
git push

echo "✅ learning-hub 合并完成" | tee -a "$LOG_FILE"

# ========== 合并到 ai-knowledge-graph ==========
echo "=== 合并到 ai-knowledge-graph ===" | tee -a "$LOG_FILE"

REPOS_AI="ai-security-governance ai-business-automation rag-knowledge-system ai-agent-workflow-engine"

for repo in $REPOS_AI; do
  echo "克隆 $repo..." | tee -a "$LOG_FILE"

  if gh repo clone "srxly888-creator/$repo" "$BACKUP_DIR/$repo" 2>&1 | tee -a "$LOG_FILE"; then
    echo "✅ 克隆成功: $repo" | tee -a "$LOG_FILE"
  else
    echo "❌ 克隆失败: $repo" | tee -a "$LOG_FILE"
    continue
  fi
done

# 创建子目录并复制
cd /Volumes/AI_LAB/Github/ai-knowledge-graph

SUBDIRS="security-governance business-automation rag-system workflow-engine"

for i in {1..4}; do
  repo=$(echo "$REPOS_AI" | awk "{print \$$i}")
  subdir=$(echo "$SUBDIRS" | awk "{print \$$i}")

  echo "创建子目录: $subdir" | tee -a "$LOG_FILE"

  mkdir -p "$subdir"
  cp -r "$BACKUP_DIR/$repo"/* "$subdir/" 2>&1 | tee -a "$LOG_FILE"
done

# 更新 README
cat >> README.md << 'EOF'

## 合并的 AI 项目
- [Security Governance](./security-governance/) - AI 安全治理
- [Business Automation](./business-automation/) - AI 业务自动化
- [RAG System](./rag-system/) - RAG 知识系统
- [Workflow Engine](./workflow-engine/) - AI 工作流引擎
EOF

# 提交
git add .
git commit -m "合并 AI 项目：security, business-automation, rag, workflow"
git push

echo "✅ ai-knowledge-graph 合并完成" | tee -a "$LOG_FILE"

# ========== 删除旧仓库 ==========
echo "=== 删除旧仓库 ===" | tee -a "$LOG_FILE"

ALL_REPOS="$REPOS $REPOS_AI"

for repo in $ALL_REPOS; do
  echo "删除 $repo..." | tee -a "$LOG_FILE"

  if gh repo delete "srxly888-creator/$repo" --yes 2>&1 | tee -a "$LOG_FILE"; then
    echo "✅ 成功删除: $repo" | tee -a "$LOG_FILE"
  else
    echo "❌ 删除失败: $repo" | tee -a "$LOG_FILE"
  fi

  sleep 1
done

echo "================================" | tee -a "$LOG_FILE"
echo "合并完成!" | tee -a "$LOG_FILE"
```

## 📜 脚本 3：验证清理结果

### verify-cleanup.sh
```bash
#!/bin/bash
# 验证清理结果
# 使用方法: ./verify-cleanup.sh

echo "=== GitHub 仓库统计 ==="

# 统计剩余仓库
TOTAL=$(gh repo list srxly888-creator --limit 1000 --json name --jq 'length')
FORKS=$(gh repo list srxly888-creator --limit 1000 --json name,isFork --jq '[.[] | select(.isFork == true)] | length')
ORIGINAL=$(gh repo list srxly888-creator --limit 1000 --json name,isFork --jq '[.[] | select(.isFork == false)] | length')

echo "总仓库数: $TOTAL"
echo "Fork 仓库: $FORKS"
echo "原创仓库: $ORIGINAL"

# 统计有 stars 的仓库
STARS=$(gh repo list srxly888-creator --limit 1000 --json name,stargazerCount --jq '[.[] | select(.stargazerCount > 0)] | length')
echo "有 stars 的仓库: $STARS"

# 详细列表
echo ""
echo "=== 有 stars 的仓库 ==="
gh repo list srxly888-creator --limit 1000 --json name,stargazerCount --jq '[.[] | select(.stargazerCount > 0)] | sort_by(.stargazerCount) | reverse | .[] | "\(.name): \(.stargazerCount) stars"'
```

## 🚀 使用方法

### 1. 授权
```bash
gh auth refresh -h github.com -s delete_repo
# 在浏览器中完成授权
```

### 2. 执行删除
```bash
chmod +x delete-forks.sh
./delete-forks.sh
```

### 3. 执行合并
```bash
chmod +x merge-repos.sh
./merge-repos.sh
```

### 4. 验证结果
```bash
chmod +x verify-cleanup.sh
./verify-cleanup.sh
```

## ⚠️ 注意事项

1. **确认授权**: 必须先获得 delete_repo 权限
2. **备份重要数据**: 执行前确保重要数据已备份
3. **检查日志**: 所有操作都会记录日志
4. **逐步执行**: 建议分步执行，每步验证

---

**时间**: 2026-03-31 00:05
**状态**: 🟢 脚本准备完成
