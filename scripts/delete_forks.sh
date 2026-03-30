# GitHub 仓库批量清理脚本

> **创建时间**: 2026-03-31 04:05
> **用途**: 批量删除 63 个 Fork 仓库
> **状态**: 🔥 火力全开

---

## 📋 清单文件

### Fork 列表
**文件**: `/tmp/forks_to_delete.txt`
**数量**: 63 个
**条件**: 0 stars 的 Fork 仓库

---

## 🛠️ 清理脚本

### 1. 批量删除 Fork 脚本

```bash
#!/bin/bash
# 文件名: delete_forks.sh

FORK_LIST="/tmp/forks_to_delete.txt"
LOG_FILE="$HOME/github_cleanup_$(date +%Y%m%d_%H%M%S).log"

echo "🔥 开始批量删除 Fork..." | tee -a "$LOG_FILE"
echo "时间: $(date)" | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"

count=0
total=$(wc -l < "$FORK_LIST")

while IFS= read -r repo; do
    count=$((count + 1))
    echo "[$count/$total] 删除: $repo" | tee -a "$LOG_FILE"

    # 删除仓库
    if gh repo delete "$repo" --yes 2>&1 | tee -a "$LOG_FILE"; then
        echo "✅ 成功删除: $repo" | tee -a "$LOG_FILE"
    else
        echo "❌ 删除失败: $repo" | tee -a "$LOG_FILE"
    fi

    # 避免触发 API 限制
    sleep 1
done < "$FORK_LIST"

echo "---" | tee -a "$LOG_FILE"
echo "🎉 完成！共删除 $count 个仓库" | tee -a "$LOG_FILE"
```

### 2. 验证脚本

```bash
#!/bin/bash
# 文件名: verify_deletion.sh

FORK_LIST="/tmp/forks_to_delete.txt"

echo "🔍 验证删除结果..."

count=0
while IFS= read -r repo; do
    if gh repo view "$repo" &>/dev/null; then
        echo "❌ 仍存在: $repo"
        count=$((count + 1))
    else
        echo "✅ 已删除: $repo"
    fi
done < "$FORK_LIST"

echo "---"
echo "📊 结果: $count 个仓库仍然存在"
```

### 3. 备份脚本

```bash
#!/bin/bash
# 文件名: backup_before_delete.sh

BACKUP_DIR="$HOME/github_backup_$(date +%Y%m%d_%H%M%S)"
FORK_LIST="/tmp/forks_to_delete.txt"

mkdir -p "$BACKUP_DIR"
cd "$BACKUP_DIR"

echo "💾 开始备份 Fork..."

while IFS= read -r repo; do
    echo "克隆: $repo"
    gh repo clone "$repo" --depth=1
done < "$FORK_LIST"

echo "✅ 备份完成: $BACKUP_DIR"
```

---

## 📝 使用步骤

### 步骤 1: 获取授权
```bash
gh auth refresh -h github.com -s delete_repo
```

### 步骤 2: 备份（可选）
```bash
chmod +x backup_before_delete.sh
./backup_before_delete.sh
```

### 步骤 3: 执行删除
```bash
chmod +x delete_forks.sh
./delete_forks.sh
```

### 步骤 4: 验证结果
```bash
chmod +x verify_deletion.sh
./verify_deletion.sh
```

---

## ⚠️ 注意事项

1. **授权必需**: 需要 `delete_repo` scope
2. **不可恢复**: 删除后无法恢复（除非有备份）
3. **API 限制**: 每秒 1 次操作，避免触发限制
4. **日志记录**: 所有操作都会记录到日志文件

---

## 📊 预期结果

- **删除**: 63 个 Fork 仓库
- **保留**: 37 个原创仓库
- **节省**: GitHub 配额
- **清理**: 仓库列表更清晰

---

**创建者**: srxly888-creator
**时间**: 2026-03-31 04:05
