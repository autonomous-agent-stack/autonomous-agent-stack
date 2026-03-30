# GitHub 仓库合并脚本

> **创建时间**: 2026-03-31 04:05
> **用途**: 合并 7 个原创仓库到主仓库
> **状态**: 🔥 火力全开

---

## 📋 合并计划

### 1. 合并到 openclaw-memory
- **源仓库**:
  - knowledge-vault
  - ai-tools-compendium
  - ai-agent-learning-hub

### 2. 合并到 claude-cookbooks-zh
- **源仓库**:
  - claude_cli-private
  - claude_cli-temp

### 3. 独立保留
- autonomous-agent-stack
- ClawX
- claude_cli

---

## 🛠️ 合并脚本

### 1. 准备合并脚本

```bash
#!/bin/bash
# 文件名: merge_repos.sh

TARGET_REPO="srxly888-creator/openclaw-memory"
SOURCE_REPOS=("knowledge-vault" "ai-tools-compendium" "ai-agent-learning-hub")
TEMP_DIR="/tmp/merge_$(date +%Y%m%d_%H%M%S)"

echo "🔥 开始合并仓库..."
echo "目标: $TARGET_REPO"
echo "源: ${SOURCE_REPOS[@]}"

# 创建临时目录
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# 克隆目标仓库
echo "📥 克隆目标仓库..."
gh repo clone "$TARGET_REPO" target

# 合并每个源仓库
for repo in "${SOURCE_REPOS[@]}"; do
    echo "---"
    echo "📦 处理: $repo"

    # 克隆源仓库
    gh repo clone "srxly888-creator/$repo" "$repo"

    # 复制内容到目标仓库的子目录
    mkdir -p "target/archived/$repo"
    cp -r "$repo"/* "target/archived/$repo/"

    echo "✅ 完成: $repo"
done

# 提交更改
cd target
git add -A
git commit -m "📦 合并仓库: ${SOURCE_REPOS[@]}

✅ 合并内容：
$(printf '- %s\n' "${SOURCE_REPOS[@]}")

🔥 火力全开 × 10"

git push

echo "---"
echo "🎉 合并完成！"
```

### 2. 验证合并脚本

```bash
#!/bin/bash
# 文件名: verify_merge.sh

TARGET_REPO="srxly888-creator/openclaw-memory"
MERGED_DIRS=("archived/knowledge-vault" "archived/ai-tools-compendium" "archived/ai-agent-learning-hub")

echo "🔍 验证合并结果..."

gh repo clone "$TARGET_REPO" /tmp/verify_merge
cd /tmp/verify_merge

for dir in "${MERGED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        files=$(find "$dir" -type f | wc -l)
        echo "✅ $dir: $files 个文件"
    else
        echo "❌ $dir: 不存在"
    fi
done

echo "✅ 验证完成"
```

---

## 📝 使用步骤

### 步骤 1: 备份源仓库
```bash
# 手动备份到本地
cd ~/github_GZ
tar -czf backup_repos_$(date +%Y%m%d).tar.gz \
    knowledge-vault \
    ai-tools-compendium \
    ai-agent-learning-hub
```

### 步骤 2: 执行合并
```bash
chmod +x merge_repos.sh
./merge_repos.sh
```

### 步骤 3: 验证结果
```bash
chmod +x verify_merge.sh
./verify_merge.sh
```

### 步骤 4: 删除源仓库（可选）
```bash
# 确认合并成功后再删除
gh repo delete srxly888-creator/knowledge-vault --yes
gh repo delete srxly888-creator/ai-tools-compendium --yes
gh repo delete srxly888-creator/ai-agent-learning-hub --yes
```

---

## ⚠️ 注意事项

1. **备份优先**: 合并前务必备份
2. **历史保留**: Git 历史会丢失（因为是复制文件）
3. **验证后删除**: 确认合并成功后再删除源仓库
4. **更新引用**: 更新相关文档和链接

---

## 📊 预期结果

- **保留**: 4 个核心仓库
- **合并**: 3 个仓库到 openclaw-memory
- **删除**: 3 个空仓库（合并后）
- **节省**: 管理成本

---

**创建者**: srxly888-creator
**时间**: 2026-03-31 04:05
